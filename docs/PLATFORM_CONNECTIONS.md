# TYB platform connections and current status

## Dedicated infrastructure

- GitHub repository: https://github.com/akki2131/tyb-reel-automation
- Supabase project: TYB Reel Automation
- Supabase project ref: chclxenakskkdpgbidqm
- Region: ap-south-1 (Mumbai)
- Project URL: https://chclxenakskkdpgbidqm.supabase.co
- Private Storage bucket: `tyb-reels` (100 MiB object limit; ZIP uploads allowed)
- Exducate project is not used by this application and has not been changed.

## Current Supabase schema

- `tyb_reel_jobs` — job state and output references
- `tyb_reels` — Reel metadata and Instagram media IDs
- `tyb_rotation_state` — reserved for future transactional state; the first renderer currently persists its proven JSON rotation file in private Storage
- `tyb_reel_insight_snapshots` — dated Instagram metrics
- `tyb_learnings` — evidence-backed learning candidates

RLS is enabled and direct access from anon/authenticated roles is revoked. The Storage bucket is private. The workflow currently persists the renderer's JSON rotation state in Storage; the database rotation-state table is reserved for a later transactional worker integration. Privileged access must remain server-side.

## GitHub Actions

Two manual workflows are committed:
- `Generate TYB Reel` — imports the prototype from private Storage, runs the Python renderer, and uploads output artifacts.
- `Deploy TYB Supabase Function` — deploys the TYB Insights function only to the dedicated TYB project.

Required GitHub Actions repository secrets:
- `OPENAI_API_KEY` — TYB-specific OpenAI API key.
- `SUPABASE_ACCESS_TOKEN` — Supabase personal access token for function deployment.
- `SUPABASE_SERVICE_ROLE_KEY` — Supabase server-side service-role key used only to download the private prototype archive in the workflow.

Required GitHub Actions repository variable:
- `SUPABASE_URL` — `https://chclxenakskkdpgbidqm.supabase.co`.

Optional repository variable:
- `OPENAI_MODEL` — defaults to `gpt-4.1-mini`.

### One-time prototype upload

Upload the supplied ZIP to the private bucket at the exact object path:
`source/TYB_Reel_Generator_v1.zip`

Use the Supabase Storage dashboard for the `tyb-reels` bucket. The ZIP is approximately 39 MB, below the bucket's 100 MiB object limit. The workflow downloads it securely at runtime and extracts only the required source and assets. Do not make the bucket public.

## Instagram Insights function

The isolated Supabase Edge Function `fetch-tyb-reel-insights` is deployed with JWT verification enabled. It reads recent Instagram media, stores Reel metadata, fetches media-insight metrics, and records dated success/error snapshots. The same function source is committed in the TYB repository.

It is not yet operational because TYB Instagram credentials and the Graph API version have not been configured or tested. The function currently targets Instagram API with Instagram Login (`graph.instagram.com`), so the connected professional account's token needs the `instagram_business_basic` and `instagram_business_manage_insights` permissions. Do not mix a Facebook Login token/permission model with this endpoint. Add these **Supabase Edge Function secrets** in the TYB project:
- `TYB_INSTAGRAM_ACCESS_TOKEN`
- `TYB_INSTAGRAM_USER_ID`
- `TYB_GRAPH_API_VERSION` (current supported version for the connected Instagram API product)

The function uses Supabase's server-side secret key environment for database writes. Never put Instagram tokens or Supabase secret/service-role keys in browser code, GitHub source, or chat.

## Remaining connection steps

1. Upload the prototype ZIP to the private Storage path specified above.
2. Add the TYB OpenAI key, Supabase access token, and service-role key as GitHub Actions secrets; add `SUPABASE_URL` as a repository variable.
3. Add the three Instagram secrets above in Supabase and authorise the correct Instagram professional account with the required insights permissions.
4. Run the manual Supabase deployment workflow if you later change the function source.
5. Invoke the deployed function with an authorised Supabase credential and verify successful snapshots against the account.
6. Connect the Python renderer to the Supabase job/state/storage tables, then test the end-to-end workflow.
7. Build the learning-analysis step only after real insights are collecting reliably. Automatic publishing is not part of the current deployment.
