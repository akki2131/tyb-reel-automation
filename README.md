# TYB Reel Automation

Online generator for The Yogic Belief's text-only Instagram Reels.

## Current status

This repository is being set up as a separate TYB project. The local prototype and assets are supplied separately in `TYB_Reel_Generator_v1.zip`; binary assets have not yet been installed in this repository or an online asset store.

The existing Exducate Supabase project is intentionally not used or modified.

## Intended first milestone

A manually triggered GitHub Actions workflow should:
1. Select the next approved question.
2. Generate and validate a customer–chef script.
3. Render a 1080 × 1920 MP4 using the supplied templates, Lobster font, CTA image, and music.
4. Save the MP4, cover, script, and rotation state as a downloadable workflow artifact.

This first milestone generates files for review. It does not publish to Instagram.

## Required configuration

The workflow will need an `OPENAI_API_KEY` GitHub Actions secret. Rendering also requires the supplied Question Bank, visual assets, CTA artwork, music files, and a usable Lobster font file to be available to the runner.

Do not commit API keys or other credentials.

## Brand and sequence invariants

- Only questions from `TYB_Question_Bank_v2.xlsx` are eligible.
- The approved question must be reproduced exactly as the first customer scene.
- Do not mention specific menu-item names in the Reel, cover, or associated copy.
- Template pairs rotate 1 → 2 → 3 → 4.
- Music rotates BGM 1 → 5.
- Approved CTA messages rotate 1 → 8. CTA 8 must remain exactly: `Share this with a health phile you know.`
- Question and asset rotations advance only after a successful render and saved output record.
- Rendering and Instagram publishing are separate operations.

## Cost and publishing

No paid infrastructure has been provisioned by this repository setup. GitHub Actions usage, AI API usage, and any future storage/runtime costs depend on account limits and execution volume. Instagram publishing is not implemented or authorised by this initial setup.
