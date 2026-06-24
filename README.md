WHY THE JPGS WERE BREAKING — AND THE PERMANENT FIX
=====================================================

WHAT I FOUND
-------------
I pulled the live poller.py straight from your GitHub repo and tested every
card generator end-to-end. The image-saving code itself is clean: every
card (result, schedule, recap, prediction) saves as a proper baseline
JPEG, 1080x1080, RGB, no CMYK, no progressive encoding, no corrupt
segments — I verified this at the byte level. Instagram has no reason to
reject these files as generated.

The actual problem is the DELIVERY PATH, not the generation. Your pipeline
was: poller saves JPEG → uploads to Dropbox → Dropbox syncs to your phone
→ you open the Dropbox app → share to Instagram. Dropbox's mobile sync
uses lazy "online-only" placeholders — the file icon and thumbnail can
show up before the actual bytes have finished downloading to your phone.
If you tap "share to Instagram" in that window, IG's share sheet can grab
a partial or empty file, even though the real file sitting in Dropbox's
cloud storage is completely fine. This matches the same failure signature
as the 0-byte uploads from earlier in the tournament — except this time
the file is fine all the way up to Dropbox, and breaks on the way back
down to your phone.

THE PERMANENT FIX
-------------------
I removed Dropbox from the posting path entirely. Dropbox now only
receives a backup copy (and a failure to upload there is logged but no
longer blocks anything).

Instead, the poller now runs a small web server on the same process,
which serves every card directly off disk:

  GET  /              → mobile-friendly feed page, newest card first,
                          tap to view full-size, caption shown underneath
                          for one-tap copy/paste into Instagram
  GET  /card/<file>    → the actual image, byte-verified on disk at the
                          moment of the request (refuses to serve anything
                          under 30KB — you'll get a clean 410 error
                          instead of a broken file)
  GET  /feed.json      → machine-readable feed with direct image URLs +
                          captions, ready for a future auto-poster
  GET  /healthz        → quick check that the service is alive

Because this reads straight from the same disk the poller just wrote to,
there is no sync layer, no client-side cache, and no "online-only"
placeholder state in between. The file you see is the file that exists.

WHAT TO DO
------------
1. Push the new poller.py and requirements.txt to your GitHub repo
   (replacing the existing files — Flask was added as a dependency).
2. Railway will auto-redeploy. No new environment variables are needed —
   Railway already injects PORT automatically, and the poller now reads
   it (defaulting to 8080 if unset).
3. Once deployed, open Railway's "Settings" tab for the service and check
   that a public domain is generated/enabled (Railway does this
   automatically for any service listening on $PORT). Open that domain
   on your phone — you'll see the feed page.
4. Your new workflow: open the Railway URL on your phone → tap the
   newest card → save image / share directly to Instagram → copy the
   caption shown right under it. No Dropbox app, no sync wait.

LOOKING AHEAD: FULLY AUTOMATIC POSTING
-----------------------------------------
The /feed.json endpoint is already in the shape a real auto-poster needs.
To remove the last manual tap, Instagram's Graph API requires a Business
or Creator account linked to a Facebook Page, a Meta developer app, and
Meta App Review approval for the instagram_business_content_publish
permission — that approval process can take a couple of weeks, so it's
not something to start mid-tournament if you want zero downtime. When
you're ready, the publish flow is two calls:
  POST /{ig-user-id}/media          with image_url = your /card/<file> URL
  POST /{ig-user-id}/media_publish  with the returned creation_id
I can wire that in as a new job_autopost() the moment you have the token —
no further poller rewrites needed, since /feed.json already has
everything that call requires.

After every final whistle:
  Brazil_vs_Colombia_123456.png   ← result card
  Brazil_vs_Colombia_123456.txt   ← caption with hashtags

---

## Your posting workflow
1. Dropbox notification appears on your phone
2. Open image → looks good → tap Share
3. Open .txt file → copy caption
4. Paste into Instagram (or Buffer) → Post

Total time per post: ~30 seconds.
