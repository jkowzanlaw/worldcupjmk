# World Cup in 5 — Autonomous Instagram Poster

Posts daily schedule cards + match result cards to your Dropbox automatically.

## Files
- `poller.py` — main autonomous script
- `generate_result_card.py` — result card generator (standalone)
- `generate_schedule_card.py` — schedule card generator (standalone)
- `requirements.txt` — Python dependencies
- `render.yaml` — Render deployment config

---

## Setup (one time, ~15 minutes)

### 1. Get your Dropbox access token
1. Go to https://www.dropbox.com/developers/apps
2. Click "Create app"
3. Choose "Scoped access" → "Full Dropbox" → name it "WorldCupIn5"
4. Under "Permissions" tab, enable: `files.content.write`, `files.content.read`
5. Under "Settings" tab, scroll to "OAuth 2" → click "Generate" under Access Token
6. Copy the token — paste it in Render as DROPBOX_TOKEN

### 2. Deploy to Render
1. Push all files to a GitHub repo (github.com → New repo → upload files)
2. Go to https://render.com → New → Web Service → connect your GitHub repo
3. Change type to "Background Worker"
4. Set environment variables:
   - FOOTBALL_API_KEY = a8c2f8c622b148ac9326144ac2113336
   - DROPBOX_TOKEN    = (from step 1)
   - ANTHROPIC_API_KEY = (your Anthropic key from console.anthropic.com)
   - DROPBOX_FOLDER   = /WorldCupIn5
5. Click Deploy

### 3. Set up your phone
1. Install Dropbox on your iPhone
2. Navigate to the WorldCupIn5 folder
3. Enable notifications for that folder
4. Install Buffer or Later — connect your Instagram account
5. When a new file appears in Dropbox, open it, tap Share → Schedule in Buffer

---

## What gets posted to Dropbox

Every morning at 8am ET:
  SCHEDULE_20260612_Day2.png   ← the schedule card
  SCHEDULE_20260612_Day2.txt   ← the caption (copy/paste)

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
