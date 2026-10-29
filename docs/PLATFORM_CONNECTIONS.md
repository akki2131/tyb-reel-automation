# TYB platform connections and current status

## Dedicated infrastructure

- GitHub repository: https://github.com/akki2131/tyb-reel-automation
- Supabase project: TYB Reel Automation
- Supabase project ref: chclxenakskkdpgbidqm
- Region: ap-south-1 (Mumbai)
- Project URL: https://chclxenakskkdpgbidqm.supabase.co
- Exducate project is not used by this application and has not been changed.

## Current Supabase schema

The private application data tables are:
- `tyb_reel_jobs`
- `tyb_reels`
- `tyb_rotation_state`
- `tyb_reel_insight_snapshots`
- `tyb_learnings`

Row-level security is enabled and direct access from anon/authenticated roles is revoked. The intended server-side worker will use a secret server-side credential; never put that credential in browser code or commit it.

## GitHub Actions workflow

`.github/workflows/generate-reel.yml` adds a manual workflow dispatch and artifact output. It intentionally checks that the prototype source and all assets exist before attempting to render. The ZIP's binary assets and generator have not yet been imported to this repository, so the workflow cannot succeed until that import is completed.

Required repository secret for live generation:
- `OPENAI_API_KEY` — TYB-specific API key from the OpenAI API platform.

Optional repository variable:
- `OPENAI_MODEL` — defaults to `gpt-4.1-mini`.

## Instagram connection

No Instagram credentials are stored in this project yet. The account owner must authorise TYB's Instagram professional account through Meta and provide the required long-lived access token and Instagram user ID through the supported secret-management flow. Do not share passwords or one-time codes in chat.

The initial scope is insight collection and learning, not automatic publishing. Publishing remains a separate opt-in implementation.

## Next blockers

1. Import the prototype's Python file, workbook, constitution, templates, CTA, and music files into this repository or an authenticated private asset store.
2. Add the TYB OpenAI key as a GitHub Actions secret.
3. Set up a server-side secret for the Supabase service role key; do not use the publishable key for privileged writes.
4. Authorise Instagram and add the Instagram access token and account ID as secrets.
5. Implement the worker-to-Supabase persistence and Instagram Insights fetch, then test each integration end to end.
