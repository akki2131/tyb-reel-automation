# TYB Instagram Publishing

## Production flow

The production GitHub Actions workflow is currently **manual only**. The daily 5:30 PM IST schedule is intentionally disabled until the first published Reel has been reviewed and approved. A manually triggered production run can publish immediately when `demo=false` and `publish=true`. The workflow:
1. Generates and renders the Reel using the version-controlled generator and assets in this repository (no prototype ZIP download).
2. Generates a brand-consistent Instagram caption with the configured OpenAI model.
3. Stores the MP4, cover and enriched script JSON in the private `tyb-reels` Storage bucket.
4. Saves the caption and Reel metadata in `tyb_reels`.
5. Persists the rotation state after generation succeeds.
6. Calls the `publish-tyb-reel` Supabase Edge Function only when the manual `publish` input is true.
7. Saves the returned Instagram media ID and permalink, with publish status/error tracking.

Demo mode uses a fixed sample caption, does not create a production Reel row, and never calls the publishing function. The `publish` input defaults to false. Do not enable the daily schedule until the user explicitly approves the first published Reel.

## Required configuration

Existing GitHub Actions configuration:
- `OPENAI_API_KEY` secret
- `OPENAI_MODEL` repository variable (optional; defaults to `gpt-4.1-mini`)
- `SUPABASE_URL` repository variable
- `SUPABASE_SERVICE_ROLE_KEY` secret

Existing Supabase Edge Function secrets:
- `TYB_INSTAGRAM_ACCESS_TOKEN`
- `TYB_INSTAGRAM_USER_ID`
- `TYB_GRAPH_API_VERSION`
- Supabase server-side service key (provided by the project's existing Edge Function environment)

The System User token must include `instagram_basic`, `instagram_content_publish`, and the permissions needed for insights. The Instagram professional account must be linked to the correct Facebook Page and assigned to the System User/app.

## Collaborators

The publishing function defaults to inviting **`akshayaverma`** as the Reel collaborator. An optional Supabase Edge Function secret `TYB_INSTAGRAM_COLLABORATORS` can override this with up to three comma-separated usernames. Each invitation remains pending until the collaborator accepts it in Instagram.

## Instagram Stories

The first version publishes the Reel to the Instagram feed/Reels surface. Publishing a separate video Story is possible through Meta's content publishing API for eligible professional accounts, but it is a separate media publication—not the native Instagram action of sharing the Reel with its interactive Reel preview. Story publishing is intentionally disabled. The workflow publishes one Reel only; it does not upload duplicate media as a separate Story.

## Operational safety

- The publishing Edge Function requires JWT verification and should be called server-side.
- Never expose the Instagram access token or Supabase service-role key in client-side code or logs.
- If publishing fails, inspect the GitHub Actions run and the `publish_status` / `publish_error` fields on the Reel record before retrying.
- If Meta reports that publishing succeeded but saving the result to Supabase failed, do not blindly rerun the publishing request; verify the Reel on Instagram first to avoid a duplicate.
