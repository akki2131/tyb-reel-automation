import { createClient } from "npm:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function cleanError(value: unknown, token: string): string {
  let message = typeof value === "string" ? value : JSON.stringify(value);
  if (token) message = message.split(token).join("[REDACTED]");
  return message.slice(0, 1200);
}

function getSecretKey(): string | null {
  const legacy = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (legacy) return legacy;
  try {
    const keys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}");
    return keys.default ?? null;
  } catch {
    return null;
  }
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (req.method !== "POST") return json({ error: "Use POST." }, 405);

  const token = Deno.env.get("TYB_INSTAGRAM_ACCESS_TOKEN") ?? "";
  const instagramUserId = Deno.env.get("TYB_INSTAGRAM_USER_ID") ?? "";
  // The selected Meta Unified Login configuration uses a system-user token with the Facebook Graph API host.
  const graphVersion = Deno.env.get("TYB_GRAPH_API_VERSION") ?? "";
  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const serviceKey = getSecretKey();

  const missing = [
    ["TYB_INSTAGRAM_ACCESS_TOKEN", token],
    ["TYB_INSTAGRAM_USER_ID", instagramUserId],
    ["TYB_GRAPH_API_VERSION", graphVersion],
    ["SUPABASE_URL", supabaseUrl],
    ["Supabase server secret key", serviceKey ?? ""],
  ].filter(([, value]) => !value).map(([name]) => name);

  if (missing.length) {
    return json({
      error: "Integration is not configured yet.",
      missing,
      note: "Add Instagram credentials as Supabase Edge Function secrets. Never expose the access token in client code.",
    }, 503);
  }

  const supabase = createClient(supabaseUrl, serviceKey!, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  let limit = 20;
  try {
    const body = await req.json().catch(() => ({}));
    if (Number.isInteger(body?.limit)) limit = Math.min(50, Math.max(1, body.limit));
  } catch {
    // Default limit is used.
  }

  const mediaUrl = new URL(`https://graph.facebook.com/${graphVersion}/${encodeURIComponent(instagramUserId)}/media`);
  mediaUrl.searchParams.set("fields", "id,caption,media_type,media_product_type,timestamp,permalink");
  mediaUrl.searchParams.set("limit", String(limit));
  mediaUrl.searchParams.set("access_token", token);

  const mediaResponse = await fetch(mediaUrl);
  const mediaPayload = await mediaResponse.json().catch(() => ({}));
  if (!mediaResponse.ok || !Array.isArray(mediaPayload?.data)) {
    return json({
      error: "Instagram media lookup failed.",
      status: mediaResponse.status,
      details: cleanError(mediaPayload?.error ?? mediaPayload, token),
      hint: "This function is configured for Meta Unified Login (graph.facebook.com). Verify the system-user token, Instagram professional account ID, API version, and instagram_basic + instagram_manage_insights permissions. If using a different login flow, align the API host and token type.",
    }, 502);
  }

  const reels = mediaPayload.data.filter((m: any) =>
    m?.id && (m.media_product_type === "REELS" || (m.media_type === "VIDEO" && m.media_product_type !== "FEED"))
  );

  const metricNames = [
    "views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
  ];
  const results: Array<Record<string, unknown>> = [];

  for (const media of reels) {
    const caption = String(media.caption ?? "").slice(0, 4000);
    const question = caption.split(/\r?\n/).map((s: string) => s.trim()).find(Boolean) || "Instagram Reel";
    const reelRow = {
      question_id: `IG-${media.id}`,
      approved_question: question,
      instagram_media_id: String(media.id),
      permalink: media.permalink ?? null,
      published_at: media.timestamp ?? null,
      caption,
    };

    const { data: reel, error: upsertError } = await supabase
      .from("tyb_reels")
      .upsert(reelRow, { onConflict: "instagram_media_id" })
      .select("id,instagram_media_id")
      .single();

    if (upsertError || !reel) {
      results.push({ media_id: media.id, status: "error", stage: "database_upsert", error: upsertError?.message ?? "No row returned" });
      continue;
    }

    const insightUrl = new URL(`https://graph.facebook.com/${graphVersion}/${encodeURIComponent(String(media.id))}/insights`);
    insightUrl.searchParams.set("metric", metricNames.join(","));
    insightUrl.searchParams.set("access_token", token);

    const insightResponse = await fetch(insightUrl);
    const insightPayload = await insightResponse.json().catch(() => ({}));

    if (!insightResponse.ok || !Array.isArray(insightPayload?.data)) {
      const errorMessage = cleanError(insightPayload?.error ?? insightPayload, token);
      await supabase.from("tyb_reel_insight_snapshots").insert({
        reel_id: reel.id,
        status: "error",
        metrics: {},
        error_message: errorMessage,
      });
      results.push({ media_id: media.id, status: "error", stage: "insights", error: errorMessage });
      continue;
    }

    const metrics: Record<string, unknown> = {};
    for (const item of insightPayload.data) {
      metrics[item.name] = {
        values: item.values ?? [],
        total_value: item.total_value ?? null,
        period: item.period ?? null,
        title: item.title ?? null,
      };
    }

    const { error: snapshotError } = await supabase.from("tyb_reel_insight_snapshots").insert({
      reel_id: reel.id,
      status: "success",
      metrics,
      error_message: null,
    });

    results.push(snapshotError
      ? { media_id: media.id, status: "error", stage: "snapshot_insert", error: snapshotError.message }
      : { media_id: media.id, status: "success", metric_count: Object.keys(metrics).length });
  }

  return json({
    ok: results.every((r) => r.status === "success"),
    scanned_media: mediaPayload.data.length,
    reels_found: reels.length,
    succeeded: results.filter((r) => r.status === "success").length,
    failed: results.filter((r) => r.status === "error").length,
    results,
  });
});
