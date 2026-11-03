# TYB Instagram Publishing

## Production flow

The production GitHub Actions workflow now:
1. Generates and renders the Reel using the existing generator.
2. Generates a brand-consistent Instagram caption with the configured OpenAI model.
3. Stores the MP4, cover and enriched script JSON in the private `tyb-reels` Storage bucket.
4. Saves the caption and Reel metadata in `tyb_reels`.
5. Persists the rotation state after generation succeeds.
6. Calls the `publish-tyb-reel` Supabase Edge Function immediately.
7. Saves the returned Instagram media ID and permalink, with publish status/error tracking.

Demo mode uses a fixed sample caption, does not create a production Reel row, and never calls the publishing function.

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

The publishing function accepts up to three optional collaborator usernames from the Supabase Edge Function secret `TYB_INSTAGRAM_COLLABORATORS`, comma-separated and without the leading @ being required. Each invitation remains pending until the collaborator accepts it in Instagram. Leave this unset to publish without collaborators.

## Instagram Stories

The first version publishes the Reel to the Instagram feed/Reels surface. Publishing a separate video Story is possible through Meta's content publishing API for eligible professional accounts, but it is a separate media publication—not the native Instagram action of sharing the Reel with its interactive Reel preview. Story publishing is intentionally not enabled by default until the owner chooses the desired behavior.

## WhatsApp Status

The official WhatsApp Business Platform API does not provide a supported endpoint for publishing a WhatsApp Status. A status-ready MP4 can be generated and made available for manual sharing, but posting it directly to Status is not part of this API workflow.

## Operational safety

- The publishing Edge Function requires JWT verification and should be called server-side.
- Never expose the Instagram access token or Supabase service-role key in client-side code or logs.
- If publishing fails, inspect the GitHub Actions run and the `publish_status` / `publish_error` fields on the Reel record before retrying.
- If Meta reports that publishing succeeded but saving the result to Supabase failed, do not blindly rerun the publishing request; verify the Reel on Instagram first to avoid a duplicate.
