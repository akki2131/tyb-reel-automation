# TYB Reel Automation

Online generator and Instagram performance-learning infrastructure for The Yogic Belief's text-only Reels.

## Separate application infrastructure

- GitHub: https://github.com/akki2131/tyb-reel-automation
- Supabase project: `chclxenakskkdpgbidqm` in Mumbai (`ap-south-1`)
- Private storage bucket: `tyb-reels`
- Exducate is a separate project and is not modified or used by TYB.

## Current status

- Supabase core schema deployed and verified.
- RLS enabled on all five TYB tables; direct anon/authenticated table access is revoked.
- Private storage bucket created, with support for the supplied ZIP.
- Manual GitHub Actions workflows committed for Reel generation and TYB Edge Function deployment.
- Supabase Edge Function `fetch-tyb-reel-insights` deployed with JWT verification. It still needs TYB Instagram credentials and an API version configured before a live test.
- The generator workflow downloads the prototype ZIP from private Supabase Storage at runtime, restores the previous successful rotation state, and persists the updated state only after a successful render and artifact upload. The 39 MB asset bundle does not need to be committed into Git.

## First generation milestone

The manually triggered workflow is intended to select an approved question, generate and validate a customer–chef script, render a 1080 × 1920 MP4, and provide the MP4, cover, script, and state as a downloadable workflow artifact. This first milestone does not publish to Instagram.

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
