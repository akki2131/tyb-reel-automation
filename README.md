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
- Private storage bucket created.
- Manual GitHub Actions workflow committed. It will stop with an explicit preflight error until the prototype script and binary assets are imported.
- Supabase Edge Function `fetch-tyb-reel-insights` deployed with JWT verification. It still needs TYB Instagram credentials and an API version configured before a live test.
- The prototype ZIP's Python renderer, question bank, brand constitution, template images, CTA image, and music files are not yet present in the repository.

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

Never commit API keys or other credentials. GitHub Actions needs `OPENAI_API_KEY` for live generation. Supabase Edge Function secrets must include `TYB_INSTAGRAM_ACCESS_TOKEN`, `TYB_INSTAGRAM_USER_ID`, and `TYB_GRAPH_API_VERSION` before insight collection can be tested.

The project-creation quote was $0/month for the project itself. GitHub Actions, OpenAI usage, storage, and any additional services may still incur usage-based or account-plan costs. See [docs/PLATFORM_CONNECTIONS.md](docs/PLATFORM_CONNECTIONS.md) for the current connection checklist.
