# TYB Reel Automation

Online generator and Instagram performance-learning infrastructure for The Yogic Belief's text-only Reels.

## Separate application infrastructure

- GitHub: https://github.com/akki2131/tyb-reel-automation
- Supabase project: `chclxenakskkdpgbidqm` in Mumbai (`ap-south-1`)
- Private storage bucket: `tyb-reels`
- Exducate is a separate project and is not modified or used by TYB.

## Current status

- Supabase core schema deployed and verified; the generation workflow is wired to create job rows, store output objects privately, save Reel metadata, and update job status.
- RLS enabled on all five TYB tables; direct anon/authenticated table access is revoked.
- Private storage bucket `tyb-reels` stores generated media and persistent rotation state.
- Manual GitHub Actions workflows committed for Reel generation and TYB Edge Function deployment.
- Supabase Edge Function `fetch-tyb-reel-insights` deployed and successfully tested with the TYB Instagram System User token.
- Supabase Edge Function `publish-tyb-reel` deployed with JWT verification. Production generation now creates a brand-consistent caption, saves it with the Reel metadata, and invokes publishing immediately; demo mode never publishes.
- Automatic publishing state is tracked on `tyb_reels` using `publish_status`, `publish_error`, and `instagram_container_id`.
- The one-time generator migration completed successfully: generator Python source, the 110-question workbook, brand constitution, eight visual templates, CTA graphic, and five background tracks are now version-controlled in this repository. The production workflow uses these files directly and no longer downloads or extracts the prototype ZIP.
- The generation workflow restores rotation state from private Supabase Storage, stores generated MP4/cover/script files there, writes job and Reel records, and persists updated state after successful production generation. Demo runs do not consume rotation state.

## First generation milestone

The workflow is manually triggered. Set `demo=false` for a real AI-generated script and `publish=true` to publish immediately to Instagram after successful generation. `publish` defaults to false. The generated MP4, cover, script, and state are also provided as a downloadable workflow artifact.

## Brand and sequence invariants

- Only questions from `TYB_Question_Bank_v2.xlsx` are eligible.
- The approved question must be reproduced exactly as the first customer scene.
- Do not mention specific menu-item names in the Reel, cover, or associated copy.
- Template pairs rotate 1 → 2 → 3 → 4.
- Music rotates BGM 1 → 5.
- Approved CTA messages rotate 1 → 8. CTA 8 must remain exactly: `Share this with a health phile you know.`
- Question and asset rotations advance only after a successful render and saved output record.
- Rendering and Instagram publishing are separate operations.

## Secrets and costs

Never commit API keys or other credentials. GitHub Actions needs `OPENAI_API_KEY`, `SUPABASE_ACCESS_TOKEN`, and `SUPABASE_SERVICE_ROLE_KEY` secrets, plus the `SUPABASE_URL` repository variable. Supabase Edge Function secrets must include `TYB_INSTAGRAM_ACCESS_TOKEN`, `TYB_INSTAGRAM_USER_ID`, and `TYB_GRAPH_API_VERSION` before insight collection can be tested.

The project-creation quote was $0/month for the project itself. GitHub Actions, OpenAI usage, storage, and any additional services may still incur usage-based or account-plan costs. See [docs/PLATFORM_CONNECTIONS.md](docs/PLATFORM_CONNECTIONS.md) for the current connection checklist.

## Publishing

See [docs/PUBLISHING.md](docs/PUBLISHING.md) for the publishing flow, required configuration, optional collaborator invitations, and Story publishing limitations.
