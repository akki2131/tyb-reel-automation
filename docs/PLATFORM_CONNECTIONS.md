# TYB platform connections and current status

## Dedicated infrastructure

- GitHub repository: https://github.com/akki2131/tyb-reel-automation
- Supabase project: TYB Reel Automation
- Supabase project ref: chclxenakskkdpgbidqm
- Region: ap-south-1 (Mumbai)
- Project URL: https://chclxenakskkdpgbidqm.supabase.co
- Private Storage bucket: `tyb-reels` (100 MiB object limit)
- Exducate project is not used by this application and has not been changed.

## Current Supabase schema

- `tyb_reel_jobs` — job state and output references
- `tyb_reels` — Reel metadata and Instagram media IDs
- `tyb_rotation_state` — question, template, music, and CTA rotation state
- `tyb_reel_insight_snapshots` — dated Instagram metrics
- `tyb_learnings` — evidence-backed learning candidates

RLS is enabled and direct access from anon/authenticated roles is revoked. The Storage bucket is private. Privileged access must remain server-side.

## GitHub Actions

`.github/workflows/generate-reel.yml` adds a manual workflow dispatch and artifact output. It intentionally checks that the prototype source and all assets exist before attempting to render. The ZIP's Python generator and binary assets have not yet been imported to this repository, so the workflow cannot succeed until that import is completed.

Required GitHub Actions repository secret:
- `OPENAI_API_KEY` — a TYB-specific API key from the OpenAI API platform.

Optional GitHub Actions repository variable:
- `OPENAI_MODEL` — defaults to `gpt-4.1-mini`.

## Instagram Insights function

The isolated Supabase Edge Function `fetch-tyb-reel-insights` is deployed with JWT verification enabled. It reads recent Instagram media, stores Reel metadata, fetches supported media-insight metrics, and records dated success/error snapshots.

It is not yet operational because TYB Instagram credentials and the current Graph API version have not been configured or tested. Add these **Supabase Edge Function secrets** in the TYB project:
- `TYB_INSTAGRAM_ACCESS_TOKEN`
- `TYB_INSTAGRAM_USER_ID`
- `TYB_GRAPH_API_VERSION` (the current supported version for the connected Instagram API product)

The function uses Supabase's server-side secret key environment for database writes. Never put Instagram tokens or Supabase secret/service-role keys in browser code, GitHub source, or chat.

## Remaining connection steps

1. Import the prototype's Python file, workbook, constitution, templates, CTA, and music files into this repository or an authenticated private asset store.
2. Add the TYB OpenAI key as a GitHub Actions secret.
3. Add the three Instagram secrets above in Supabase and authorise the correct Instagram professional account with the required insights permissions.
4. Invoke the deployed function with an authorised Supabase credential and verify successful snapshots against the account.
5. Connect the Python renderer to the Supabase job/state/storage tables, then test the end-to-end workflow.
6. Build the learning-analysis step only after real insights are collecting reliably. Automatic publishing is not part of the current deployment.
