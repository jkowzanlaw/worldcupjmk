#!/usr/bin/env python3
"""
World Cup in 5 — Autonomous Poller v2
Optimized captions + hashtags for maximum Instagram reach.
"""

import os, time, json, logging, requests, schedule
from datetime import datetime, timezone, timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import dropbox

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("wc5")

FD_KEY      = os.environ["FOOTBALL_API_KEY"]
DBX_TOKEN   = os.environ["DROPBOX_TOKEN"]
CLAUDE_KEY  = os.environ["ANTHROPIC_API_KEY"]
DBX_FOLDER  = os.environ.get("DROPBOX_FOLDER", "/WorldCupIn5")
TMP_DIR     = Path("/tmp/wc5"); TMP_DIR.mkdir(exist_ok=True)
POSTED_FILE = TMP_DIR / "posted.json"
TOURNAMENT_START = datetime(2026, 6, 11, tzinfo=timezone.utc)

FONT_DIR  = Path("/tmp/fonts"); FONT_DIR.mkdir(exist_ok=True)
BEBAS     = str(FONT_DIR / "BebasNeue.ttf")
POPPINS_B = str(FONT_DIR / "Poppins-Bold.ttf")
POPPINS_M = str(FONT_DIR / "Poppins-Medium.ttf")
POPPINS_R = str(FONT_DIR / "Poppins-Regular.ttf")

# ── Optimized hashtag sets ────────────────────────────────────────────────────
# Tiered strategy: broad (volume) + mid (targeted) + niche (less competition)
CORE_HASHTAGS = [
    "#WorldCup2026", "#FIFAWorldCup", "#FWC26", "#WeAre26",
    "#WorldCup", "#Soccer", "#Football", "#FIFA",
]
MID_HASHTAGS = [
    "#WorldCupResults", "#MatchDay", "#FootballDaily",
    "#SoccerNews", "#WorldCupIn5", "#FutbolMundial",
    "#Golazo2026", "#WC2026",
]
NICHE_HASHTAGS = [
    "#FootballAnalysis", "#SoccerStats", "#MatchResult",
    "#WorldCupScores", "#FootballFans", "#SoccerFans",
    "#Somos26", "#FootballCommunity",
]

def hashtags_for_teams(home, away):
    """Add team-specific hashtags for maximum reach with those fanbases."""
    team_tags = {
        "united states": "#USMNT #USASoccer",
        "usa": "#USMNT #USASoccer",
        "mexico": "#ElTri #MexicoNT",
        "brazil": "#Selecao #BrazilNT",
        "argentina": "#Albiceleste #ArgentinaFutbol",
        "france": "#LesBleus #FranceNT",
        "england": "#ThreeLions #EnglandNT",
        "spain": "#LaRoja #SpainNT",
        "germany": "#DieManschaft #GermanyNT",
        "portugal": "#Selecao #PortugalNT",
        "canada": "#CanadaSoccer #CANMNT",
        "morocco": "#AtlasLions #MoroccoNT",
        "japan": "#SamuraiBlue #JapanNT",
        "south korea": "#TaegukWarriors #KoreaNT",
        "netherlands": "#Oranje #NetherlandsNT",
        "senegal": "#LionsDeLaTeranga #SenegalNT",
    }
    tags = []
    for team in [home.lower(), away.lower()]:
        for key, val in team_tags.items():
            if key in team:
                tags.extend(val.split())
    return tags[:4]  # max 4 team tags

def build_hashtag_block(home, away, stage):
    """Build optimized hashtag string — tiered for reach + discoverability."""
    team_tags = hashtags_for_teams(home, away)
    # Stage-specific tags
    stage_tags = []
    s = stage.lower()
    if "group" in s:        stage_tags = ["#GroupStage", "#WorldCupGroupStage"]
    elif "round of 16" in s: stage_tags = ["#RoundOf16", "#R16"]
    elif "quarter" in s:    stage_tags = ["#Quarterfinal", "#WorldCupQF"]
    elif "semi" in s:       stage_tags = ["#Semifinal", "#WorldCupSF"]
    elif "final" in s:      stage_tags = ["#WorldCupFinal", "#TheFinal"]

    all_tags = CORE_HASHTAGS + MID_HASHTAGS + stage_tags + team_tags + NICHE_HASHTAGS
    # Deduplicate, keep order, limit to 30 (Instagram best practice)
    seen = set(); final = []
    for t in all_tags:
        if t not in seen: seen.add(t); final.append(t)
    return " ".join(final[:30])

# ── Claude API ────────────────────────────────────────────────────────────────
def claude_call(prompt, max_tokens=300):
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":CLAUDE_KEY,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":max_tokens,
                  "messages":[{"role":"user","content":prompt}]},
            timeout=30
        )
        r.raise_for_status()
        text = r.json()["content"][0]["text"].strip()
        if not text:
            raise ValueError("Empty response from Claude")
        return text
    except Exception as e:
        log.error(f"Claude API error: {e}")
        return None

def claude_insight(home, away, hs, as_, stage):
    result = claude_call(
        f"Write ONE punchy sentence (max 18 words) as a match insight for Instagram. "
        f"Match: {home} {hs}\u2013{as_} {away}. Stage: {stage}. "
        f"Sound like a sharp sports journalist. No quotes, no hashtags.",
        max_tokens=80
    )
    if not result:
        if hs > as_: result = f"{home} take all three points with a {hs}\u2013{as_} victory."
        elif as_ > hs: result = f"{away} claim a crucial {as_}\u2013{hs} win over {home}."
        else: result = f"{home} and {away} share the spoils in a {hs}\u2013{as_} draw."
    return result

def claude_result_caption(home, away, hs, as_, stage, insight, hashtags):
    prompt = (
        f"Write an Instagram caption for this World Cup result.\n\n"
        f"RESULT: {home} {hs}\u2013{as_} {away} | {stage}\n"
        f"KEY INSIGHT: {insight}\n\n"
        f"FORMAT:\n"
        f"Line 1: Bold result statement with score (1 emoji max \u26bd or \U0001f525)\n"
        f"Line 2: One sharp tactical or storyline observation\n"
        f"Line 3: What this result means for the tournament\n"
        f"[blank line]\n"
        f"{hashtags}\n\n"
        f"Rules: Max 150 words before hashtags. No cliches. Sound like an expert."
    )
    result = claude_call(prompt, max_tokens=400)
    if not result:
        result = (
            f"\u26bd {home} {hs}\u2013{as_} {away}\n"
            f"{insight}\n"
            f"Full breakdown in our story.\n\n"
            f"{hashtags}"
        )
    return result

def claude_schedule_caption(matches, date_str, day_num, hashtags):
    match_lines = "\n".join([
        f"- {m['time']}: {m['home']} vs {m['away']} ({m.get('group', m.get('stage', ''))})"
        for m in matches
    ])
    prompt = (
        f"Write an Instagram caption for a World Cup daily schedule post.\n\n"
        f"DATE: {date_str} \u2014 Day {day_num} of the 2026 FIFA World Cup\n"
        f"MATCHES TODAY:\n{match_lines}\n\n"
        f"FORMAT:\n"
        f"Line 1: Punchy opener creating urgency (1 emoji max)\n"
        f"Line 2-3: 1-2 most compelling matchups with one reason each\n"
        f"Line 4: CTA to save post or turn on notifications\n"
        f"[blank line]\n"
        f"{hashtags}\n\n"
        f"Rules: Max 120 words before hashtags. No generic filler."
    )
    result = claude_call(prompt, max_tokens=350)
    if not result:
        lines = [f"\u26bd {m['home']} vs {m['away']}" for m in matches[:3]]
        result = (
            f"Day {day_num} is here \u2014 {len(matches)} matches today!\n"
            + "\n".join(lines)
            + f"\n\nSave this post and follow for live results.\n\n{hashtags}"
        )
    return result

# ── Football Data API ─────────────────────────────────────────────────────────
def fd_get(path, retries=3):
    """Fetch from football-data.org with rate-limit handling and retries."""
    for attempt in range(retries):
        try:
            r = requests.get(
                f"https://api.football-data.org/v4{path}",
                headers={"X-Auth-Token": FD_KEY}, timeout=15
            )
            if r.status_code == 429:
                wait = int(r.headers.get("X-RequestCounter-Reset", 60))
                log.warning(f"Rate limited — waiting {wait}s before retry {attempt+1}/{retries}")
                time.sleep(wait)
                continue
            if r.status_code == 403:
                log.error(f"API forbidden — check plan limits: {path}")
                return {}
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            log.warning(f"API timeout on attempt {attempt+1}: {path}")
            time.sleep(10)
        except Exception as e:
            log.error(f"API error on attempt {attempt+1}: {e}")
            time.sleep(5)
    log.error(f"fd_get failed after {retries} attempts: {path}")
    return {}

# ── ET timezone helper (EDT = UTC-4, fixed for World Cup duration June-July) ──
ET = timezone(timedelta(hours=-4))

def utc_to_et(utc_str):
    """Parse UTC ISO string and return ET datetime."""
    dt = datetime.fromisoformat(utc_str.replace("Z","+00:00"))
    return dt.astimezone(ET)

def et_now():
    """Current time in ET."""
    return datetime.now(ET)

def et_today():
    """Today's date string in ET (YYYY-MM-DD)."""
    return et_now().strftime("%Y-%m-%d")

def get_matches_for_et_date(et_date_str):
    """Fetch all WC matches whose ET kickoff date = given ET date string YYYY-MM-DD."""
    et_date = datetime.strptime(et_date_str, "%Y-%m-%d").replace(tzinfo=ET)
    utc_start = et_date_str
    utc_end = (et_date + timedelta(days=1)).strftime("%Y-%m-%d")
    data = fd_get(f"/competitions/WC/matches?dateFrom={utc_start}&dateTo={utc_end}")
    matches = data.get("matches", [])
    result = []
    for m in matches:
        m_et = utc_to_et(m["utcDate"])
        if m_et.strftime("%Y-%m-%d") == et_date_str:
            result.append(m)
    log.debug(f"get_matches_for_et_date({et_date_str}): {len(result)} matches")
    return result

def get_todays_matches():
    """Fetch all WC matches for today in ET."""
    return get_matches_for_et_date(et_today())

def get_recent_unposted_matches():
    """Fetch finished matches from today AND yesterday ET that havent been posted yet.
    Catches late games that finished after midnight or API delays."""
    today = et_today()
    yesterday = (et_now() - timedelta(days=1)).strftime("%Y-%m-%d")
    matches = get_matches_for_et_date(today) + get_matches_for_et_date(yesterday)
    # Deduplicate by match id
    seen = set(); unique = []
    for m in matches:
        if m["id"] not in seen:
            seen.add(m["id"]); unique.append(m)
    return unique

def format_kickoff_et(utc_str):
    """Format UTC kickoff time as 12-hour ET string e.g. '3:00 PM ET'."""
    et = utc_to_et(utc_str)
    hour12 = et.hour % 12 or 12
    ampm = "AM" if et.hour < 12 else "PM"
    mins = et.strftime('%M')
    return f"{hour12}:{mins} {ampm} ET"

def match_stage_label(match):
    stage = match.get("stage","").replace("_"," ").title()
    group = match.get("group","")
    if group: return f"{stage} · {group.replace('GROUP_','Group ')}"
    return stage

def day_number():
    """Day number based on ET date so midnight ET doesn't flip to next day early."""
    today = et_now().date()
    start = TOURNAMENT_START.astimezone(ET).date()
    return max(1, (today - start).days + 1)

# ── Dropbox ───────────────────────────────────────────────────────────────────
def upload_dropbox(local_path, filename):
    dbx = dropbox.Dropbox(
        oauth2_refresh_token=DBX_TOKEN,
        app_key=os.environ.get("DROPBOX_APP_KEY","gmao4qdft812tm6"),
        app_secret=os.environ.get("DROPBOX_APP_SECRET","c0xopjcwq0ty2y7")
    )
    remote = f"{DBX_FOLDER}/{filename}"
    with open(local_path,"rb") as f:
        dbx.files_upload(f.read(), remote, mode=dropbox.files.WriteMode.overwrite)
    log.info(f"Uploaded → Dropbox:{remote}")

def save_caption_file(caption, base_name):
    p = TMP_DIR / f"{base_name}.txt"
    p.write_text(caption, encoding="utf-8")
    upload_dropbox(str(p), f"{base_name}.txt")

# ── State ─────────────────────────────────────────────────────────────────────
def load_posted():
    if POSTED_FILE.exists():
        return set(json.loads(POSTED_FILE.read_text()))
    try:
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=DBX_TOKEN,
            app_key=os.environ.get("DROPBOX_APP_KEY","gmao4qdft812tm6"),
            app_secret=os.environ.get("DROPBOX_APP_SECRET","c0xopjcwq0ty2y7")
        )
        _, res = dbx.files_download(f"{DBX_FOLDER}/.posted.json")
        data = set(json.loads(res.content))
        POSTED_FILE.write_text(json.dumps(list(data)))
        log.info(f"Restored posted.json from Dropbox ({len(data)} entries)")
        return data
    except Exception:
        return set()

def save_posted(posted):
    POSTED_FILE.write_text(json.dumps(list(posted)))
    try:
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=DBX_TOKEN,
            app_key=os.environ.get("DROPBOX_APP_KEY","gmao4qdft812tm6"),
            app_secret=os.environ.get("DROPBOX_APP_SECRET","c0xopjcwq0ty2y7")
        )
        dbx.files_upload(
            json.dumps(list(posted)).encode(),
            f"{DBX_FOLDER}/.posted.json",
            mode=dropbox.files.WriteMode.overwrite
        )
    except Exception as e:
        log.warning(f"Could not backup posted.json: {e}")

def schedule_done_today():
    return (TMP_DIR / f"sched_{et_today().replace('-','')}.done").exists()

def mark_schedule_done():
    (TMP_DIR / f"sched_{et_today().replace('-','')}.done").touch()

# ── Font download ─────────────────────────────────────────────────────────────
def download_fonts():
    fonts = {
        BEBAS:     "https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf",
        POPPINS_B: "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf",
        POPPINS_M: "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Medium.ttf",
        POPPINS_R: "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf",
    }
    for path, url in fonts.items():
        if not Path(path).exists():
            log.info(f"Downloading font: {Path(path).name}")
            Path(path).write_bytes(requests.get(url, timeout=30).content)
    log.info("Fonts ready")

# ── Graphic generators ────────────────────────────────────────────────────────
def lf(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

def hr(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def darken(h,f=0.62): r,g,b=hr(h); return (int(r*f),int(g*f),int(b*f))

TEAM_COLORS = {
    "argentina":"#74ACDF","brazil":"#009C3B","france":"#002395","england":"#CF142B",
    "spain":"#AA151B","germany":"#222222","portugal":"#006600","united states":"#B22234",
    "usa":"#B22234","mexico":"#006847","canada":"#D80621","morocco":"#C1272D",
    "japan":"#BC002D","netherlands":"#E77728","uruguay":"#5EB6E4","senegal":"#00853F",
    "croatia":"#D4263D","colombia":"#C8A84B","nigeria":"#008751","australia":"#C8A84B",
    "türkiye":"#E30A17","turkey":"#E30A17","south korea":"#CD2E3A","iran":"#239F40",
    "poland":"#DC143C","ecuador":"#C8A84B","paraguay":"#D52B1E","czechia":"#D7141A",
    "switzerland":"#D52B1E","denmark":"#C60C30","serbia":"#C6363C",
    "south africa":"#007A4D","saudi arabia":"#006C35","ghana":"#006B3F",
}
PITCH_DARK=(34,80,18); PITCH_MID=(44,100,24); PITCH_EDGE=(22,55,10)

def get_accent(name):
    n = name.lower()
    for k,v in TEAM_COLORS.items():
        if k in n: return v
    return "#1a5c2a"

def centered(d,text,font,y,W,color,shadow=None):
    bb=d.textbbox((0,0),text,font=font); w=bb[2]-bb[0]; x=(W-w)//2
    if shadow: d.text((x+3,y+3),text,font=font,fill=shadow)
    d.text((x,y),text,font=font,fill=color)

def col_text(d,text,font,y,cx,color):
    bb=d.textbbox((0,0),text,font=font); w=bb[2]-bb[0]
    d.text((cx-w//2,y),text,font=font,fill=color)

def wrap_text(d,text,font,max_w):
    words=text.split(); lines=[]; line=[]
    for w in words:
        if d.textbbox((0,0)," ".join(line+[w]),font=font)[2]>max_w:
            if line: lines.append(" ".join(line))
            line=[w]
        else: line.append(w)
    if line: lines.append(" ".join(line))
    return lines

def draw_pitch(d,S,top_h):
    sw=54
    for x in range(0,S,sw*2):
        d.rectangle([x,0,min(x+sw,S),top_h],fill=PITCH_DARK)
        d.rectangle([min(x+sw,S),0,min(x+sw*2,S),top_h],fill=PITCH_MID)
    for i in range(22): d.rectangle([i,i,S-i,top_h-i],outline=(0,0,0,int(80*(1-i/22))),width=1)
    cxp,cyp,r=S//2,int(top_h*0.52),175
    for t in range(3): d.ellipse([cxp-r+t,cyp-r+t,cxp+r-t,cyp+r-t],outline=(255,255,255,25),width=1)
    d.ellipse([cxp-4,cyp-4,cxp+4,cyp+4],fill=(255,255,255,40))

def safe_save(img, output_path, min_kb=50):
    """Save image to a temp file, validate size, then move to final path.
    Raises ValueError if file is too small (corrupt/empty)."""
    tmp = Path(str(output_path) + ".tmp")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(str(tmp), "PNG")
    size_kb = tmp.stat().st_size / 1024
    if size_kb < min_kb:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"Generated image too small ({size_kb:.1f}KB < {min_kb}KB) — aborting upload")
    tmp.rename(output_path)
    log.info(f"Saved {Path(output_path).name} ({size_kb:.0f}KB)")
    return output_path

def make_result_card(home,away,hs,as_,stage,venue,insight,date_str,output_path):
    S=1080; SPLIT=555; W=(255,255,255); INK=(12,12,22)
    img=Image.new("RGB",(S,S),"#FFFFFF"); d=ImageDraw.Draw(img)
    won=home if hs>as_ else (away if as_>hs else None)
    ax=get_accent(won) if won else "#1a5c2a"; ac=hr(ax); adk=darken(ax)
    draw_pitch(d,S,SPLIT)
    d.rectangle([0,SPLIT,S,S],fill=(252,252,252))
    d.rectangle([0,SPLIT,S,SPLIT+8],fill=ac)
    f_stg=lf(POPPINS_B,26); f_tm=lf(BEBAS,96); f_sc=lf(BEBAS,260)
    f_bdg=lf(POPPINS_B,29); f_ins=lf(POPPINS_B,37); f_ven=lf(POPPINS_R,23); f_br=lf(POPPINS_B,21)
    centered(d,stage.upper(),f_stg,28,S,(205,230,205))
    badge=f"{home.upper()} WIN" if hs>as_ else (f"{away.upper()} WIN" if as_>hs else "DRAW")
    bb=d.textbbox((0,0),badge,font=f_bdg); bw=bb[2]-bb[0]+44; bx=(S-bw)//2
    d.rounded_rectangle([bx,68,bx+bw,112],radius=7,fill=ac)
    centered(d,badge,f_bdg,76,S,W)
    HL,HR=S//4,S*3//4; ty=130
    for name,ccx in [(home.upper(),HL),(away.upper(),HR)]:
        nbb=d.textbbox((0,0),name,font=f_tm); nw=nbb[2]-nbb[0]
        d.text((ccx-nw//2+3,ty+3),name,font=f_tm,fill=(0,0,0,90))
        d.text((ccx-nw//2,ty),name,font=f_tm,fill=W)
    for ccx in [HL,HR]: d.rectangle([ccx-26,ty+98,ccx+26,ty+103],fill=ac)
    sc=f"{hs}  –  {as_}"
    scbb=d.textbbox((0,0),sc,font=f_sc); scw=scbb[2]-scbb[0]; scx=(S-scw)//2
    scy=int(SPLIT*0.52)-(scbb[3]-scbb[1])//2+20
    d.text((scx+5,scy+5),sc,font=f_sc,fill=(0,0,0,100))
    d.text((scx,scy),sc,font=f_sc,fill=W)
    lines=wrap_text(d,insight,f_ins,S-100); iy=SPLIT+28
    for i,ln in enumerate(lines[:3]): centered(d,ln,f_ins,iy+i*52,S,INK)
    iy_end=iy+len(lines[:3])*52
    vy=max(iy_end+30,870)
    centered(d,venue.upper(),f_ven,vy,S,(145,145,152))
    centered(d,date_str,f_ven,vy+32,S,(160,160,168))
    d.rectangle([0,S-62,S,S],fill=PITCH_DARK); d.rectangle([0,S-62,S,S-58],fill=PITCH_EDGE)
    centered(d,"WORLD CUP IN 5  ·  2026",f_br,S-44,S,W)
    safe_save(img, output_path)
    return output_path

def make_schedule_card(matches,date_str,day_num,output_path):
    S=1080; img=Image.new("RGB",(S,S),"#FFFFFF"); d=ImageDraw.Draw(img)
    NAVY=(10,18,45); GOLD=(212,168,75); GOLD_LT=(240,215,140); GOLD_DK=(160,122,40)
    OFF_W=(252,250,245); MID=(28,42,80); MUTED=(120,130,155); W=(255,255,255)
    HH=292
    d.rectangle([0,0,S,HH],fill=NAVY)
    for i in range(0,80,8): d.line([(0,180+i),(120+i,60)],fill=(30,48,100),width=1)
    d.rectangle([0,HH,S,HH+10],fill=GOLD); d.rectangle([0,HH+10,S,S],fill=OFF_W)
    f_ey=lf(POPPINS_B,22); f_dy=lf(BEBAS,130); f_dt=lf(POPPINS_B,32)
    f_sh=lf(POPPINS_M,22); f_br=lf(POPPINS_B,20)
    centered(d,"2026 FIFA WORLD CUP  ·  TODAY'S MATCHES",f_ey,28,S,GOLD)
    centered(d,f"DAY {day_num}",f_dy,52,S,W)
    centered(d,date_str.upper(),f_dt,186,S,GOLD_LT)
    mc=f"{len(matches)} MATCH{'ES' if len(matches)!=1 else ''} TODAY"
    mcbb=d.textbbox((0,0),mc,font=f_sh); mcw=mcbb[2]-mcbb[0]+38; mcx=(S-mcw)//2
    d.rounded_rectangle([mcx,234,mcx+mcw,274],radius=6,fill=MID)
    centered(d,mc,f_sh,240,S,GOLD_LT)
    n=len(matches); pad_x=48; FOOTER=62
    body_top=HH+10; body_bot=S-FOOTER
    row_h=(body_bot-body_top-20)//n; start_y=body_top+10
    if row_h>=180:   tf=lf(BEBAS,80); tif=lf(POPPINS_B,30); gf=lf(POPPINS_M,23)
    elif row_h>=130: tf=lf(BEBAS,64); tif=lf(POPPINS_B,26); gf=lf(POPPINS_M,20)
    elif row_h>=100: tf=lf(BEBAS,52); tif=lf(POPPINS_B,22); gf=lf(POPPINS_M,17)
    else:            tf=lf(BEBAS,44); tif=lf(POPPINS_B,18); gf=lf(POPPINS_M,15)
    for i,m in enumerate(matches):
        y=start_y+i*row_h; ym=y+row_h//2
        d.rectangle([pad_x,y+4,S-pad_x,y+row_h-4],fill=(244,242,238) if i%2==0 else W)
        d.rectangle([pad_x,y+4,pad_x+5,y+row_h-4],fill=GOLD)
        tb=d.textbbox((0,0),m["time"],font=tif); th=tb[3]-tb[1]
        d.text((pad_x+18,ym-th//2-8),m["time"],font=tif,fill=NAVY)
        if m.get("group"): d.text((pad_x+18,ym+6),m["group"],font=gf,fill=MUTED)
        tc=(pad_x+190+(S-pad_x))//2
        hu=m["home"].upper(); au=m["away"].upper()
        hb=d.textbbox((0,0),hu,font=tf); hw=hb[2]-hb[0]
        ab=d.textbbox((0,0),au,font=tf); aw=ab[2]-ab[0]
        vb=d.textbbox((0,0),"vs",font=gf); vw=vb[2]-vb[0]
        g2=16; tw=hw+g2+vw+g2+aw; tx=tc-tw//2; ty2=ym-(hb[3]-hb[1])//2-4
        # Scale down font if combined team names are too wide
        max_team_w = S - pad_x - tc - 20
        while tw > (S - pad_x*2 - 200) and tf.size > 28:
            tf = lf(BEBAS, tf.size - 4)
            hb=d.textbbox((0,0),hu,font=tf); hw=hb[2]-hb[0]
            ab=d.textbbox((0,0),au,font=tf); aw=ab[2]-ab[0]
            tw=hw+g2+vw+g2+aw; tx=tc-tw//2; ty2=ym-(hb[3]-hb[1])//2-4
        d.text((tx,ty2),hu,font=tf,fill=NAVY)
        d.text((tx+hw+g2,ym-(vb[3]-vb[1])//2),"vs",font=gf,fill=MUTED)
        d.text((tx+hw+g2+vw+g2,ty2),au,font=tf,fill=NAVY)
        if i<n-1: d.rectangle([pad_x+5,y+row_h-1,S-pad_x,y+row_h],fill=(220,218,212))
    d.rectangle([0,S-FOOTER,S,S],fill=NAVY); d.rectangle([0,S-FOOTER,S,S-FOOTER+4],fill=GOLD_DK)
    centered(d,"WORLD CUP IN 5  ·  2026  ·  ALL TIMES ET",f_br,S-42,S,W)
    safe_save(img, output_path)
    return output_path

# ── Core jobs ─────────────────────────────────────────────────────────────────
def job_result_cards():
    try:
        posted = load_posted()
        all_recent = get_recent_unposted_matches()
        finished = [m for m in all_recent if m["status"] in ("FINISHED","FULL_TIME","TIMED","PAUSED") and m["score"]["fullTime"]["home"] is not None]
        # Only truly finished ones (has a full time score)
        finished = [m for m in all_recent if m["status"] in ("FINISHED","FULL_TIME")]
        new = [m for m in finished if str(m["id"]) not in posted]
        if new:
            log.info(f"Poll: {len(finished)} finished, {len(new)} new to post")
        else:
            log.info(f"Poll: {len(finished)} finished, 0 new")
        if not new: log.info(f"Poll: {len(finished)} finished, 0 new"); return
        for match in new:
            mid   = str(match["id"])
            home  = match["homeTeam"]["name"]
            away  = match["awayTeam"]["name"]
            hs    = match["score"]["fullTime"]["home"]
            as_   = match["score"]["fullTime"]["away"]
            stage = match_stage_label(match)
            venue = match.get("venue","") or ""
            today = datetime.now(timezone.utc).strftime("%B %-d, %Y")
            log.info(f"New result: {home} {hs}–{as_} {away}")
            insight   = claude_insight(home, away, hs, as_, stage)
            hashtags  = build_hashtag_block(home, away, stage)
            caption   = claude_result_caption(home, away, hs, as_, stage, insight, hashtags)
            log.info(f"Insight: {insight}")
            safe = f"{home.replace(' ','_')}_vs_{away.replace(' ','_')}_{mid}"
            img_path = str(TMP_DIR / f"{safe}.png")
            make_result_card(home, away, hs, as_, stage, venue, insight, today, img_path)
            upload_dropbox(img_path, f"{safe}.png")
            save_caption_file(caption, safe)
            posted.add(mid); save_posted(posted)
            log.info(f"Posted: {safe}")
    except Exception as e:
        log.error(f"Result job error: {e}", exc_info=True)

def job_schedule_card():
    try:
        if schedule_done_today(): return
        matches_raw = get_todays_matches()
        if not matches_raw:
            log.info("No matches today"); mark_schedule_done(); return
        today_et  = datetime.now(timezone(timedelta(hours=-4)))
        date_str  = today_et.strftime("%A, %B %-d")
        dn        = day_number()
        matches   = []
        for m in sorted(matches_raw, key=lambda x: x["utcDate"]):
            group = (m.get("group","") or "").replace("GROUP_","Group ")
            stage = m.get("stage","").replace("_"," ").title()
            matches.append({"time":format_kickoff_et(m["utcDate"]),"home":m["homeTeam"]["name"],
                            "away":m["awayTeam"]["name"],"group":group,"stage":stage})
        log.info(f"Schedule: Day {dn} · {date_str} · {len(matches)} matches")
        img_path   = str(TMP_DIR / f"schedule_{today_et.strftime('%Y%m%d')}.png")
        make_schedule_card(matches, date_str, dn, img_path)
        hashtags   = build_hashtag_block("", "", "group stage")
        caption    = claude_schedule_caption(matches, date_str, dn, hashtags)
        fname      = f"SCHEDULE_{today_et.strftime('%Y%m%d')}_Day{dn}"
        upload_dropbox(img_path, f"{fname}.png")
        save_caption_file(caption, fname)
        mark_schedule_done()
        log.info(f"Schedule posted: {date_str}")
    except Exception as e:
        log.error(f"Schedule job error: {e}", exc_info=True)



# ── Recap card generator ──────────────────────────────────────────────────────
def make_recap_card(day_num, date_str, results, standings, scorers, stat_hero, output_path):
    import math
    S=1080
    BEBAS_F=BEBAS; PB=POPPINS_B; PM=POPPINS_M

    def lfr(p,s):
        try: return ImageFont.truetype(p,s)
        except: return ImageFont.load_default()

    def cxr(d,text,font,y,W,color):
        bb=d.textbbox((0,0),text,font=font); w=bb[2]-bb[0]
        d.text(((W-w)//2,y),text,font=font,fill=color)

    def sec_hdr(d,text,y,S,color=(212,168,75)):
        f=lfr(PB,14); bb=d.textbbox((0,0),text,font=f); w=bb[2]-bb[0]
        cx_pos=(S-w)//2
        d.rectangle([36,y+9,cx_pos-10,y+10],fill=(30,48,80))
        d.rectangle([cx_pos+w+10,y+9,S-36,y+10],fill=(30,48,80))
        d.text((cx_pos,y),text,font=f,fill=color); return y+22

    GOLD=(212,168,75); GOLD_DK=(160,122,40); NAVY=(10,18,45)
    WHITE=(255,255,255); MUTED=(90,110,140); ACCENT=(79,195,247)
    OFF_W=(220,228,240); GREEN=(100,210,100)

    # estimate height
    H=max(82+22+len(results)*60+8+22+18+len(standings[0]['teams'])*19+14+22+116+22+96+62, 700)
    img=Image.new("RGB",(S,H),(8,14,35)); d=ImageDraw.Draw(img)
    for r in range(max(S,H)//2,0,-3):
        t=r/(max(S,H)//2)
        d.ellipse([S//2-r,H//2-r,S//2+r,H//2+r],
                  fill=(int(8+(1-t)*5),int(14+(1-t)*12),int(35+(1-t)*10)))

    PAD=36
    d.rectangle([0,0,S,80],fill=(12,20,50))
    d.rectangle([0,78,S,82],fill=GOLD)
    cxr(d,"2026 FIFA WORLD CUP  ·  END OF DAY RECAP",lfr(PB,18),12,S,GOLD)
    cxr(d,f"DAY {day_num}  ·  {date_str.upper()}",lfr(PB,24),40,S,WHITE)
    y=96

    # Results
    y=sec_hdr(d,"TODAY'S RESULTS",y,S)
    f_res=lfr(BEBAS_F,48); f_score=lfr(BEBAS_F,56)
    for r in results:
        rh=54; ry=y
        d.rounded_rectangle([PAD,ry,S-PAD,ry+rh],radius=8,fill=(18,28,58))
        hw=r['home'].upper(); aw=r['away'].upper(); sc=r['score']
        hbb=d.textbbox((0,0),hw,font=f_res); hw_w=hbb[2]-hbb[0]
        abb=d.textbbox((0,0),aw,font=f_res); aw_w=abb[2]-abb[0]
        scbb=d.textbbox((0,0),sc,font=f_score); sc_w=scbb[2]-scbb[0]
        home_x=S//2-sc_w//2-24-hw_w; away_x=S//2+sc_w//2+24; score_x=(S-sc_w)//2
        home_col=WHITE if r.get('winner')==r['home'] else MUTED
        away_col=WHITE if r.get('winner')==r['away'] else MUTED
        score_col=GOLD if r.get('winner') else ACCENT
        d.text((home_x,ry+4),hw,font=f_res,fill=home_col)
        d.text((score_x,ry-2),sc,font=f_score,fill=score_col)
        d.text((away_x,ry+4),aw,font=f_res,fill=away_col)
        if r.get('winner'):
            bx=home_x-28 if r['winner']==r['home'] else away_x+aw_w+6
            d.rounded_rectangle([bx,ry+14,bx+22,ry+36],radius=4,fill=(60,180,80))
            d.text((bx+5,ry+17),"W",font=lfr(PB,12),fill=WHITE)
        y+=rh+6
    y+=8

    # Standings
    y=sec_hdr(d,"GROUP STANDINGS",y,S)
    n=len(standings); cols=min(n,4); col_w=(S-PAD*2)//cols
    f_gt=lfr(PM,14); f_gp=lfr(BEBAS_F,26)
    max_rows=0
    for gi,grp in enumerate(standings):
        col=gi%cols; row_idx=gi//cols
        gx=PAD+col*col_w
        gy=y+row_idx*(len(grp['teams'])*19+32)
        d.text((gx+4,gy),f"GROUP {grp['group']}",font=lfr(PB,15),fill=ACCENT)
        d.text((gx+col_w-86,gy),"P",font=lfr(PM,11),fill=MUTED)
        d.text((gx+col_w-58,gy),"GD",font=lfr(PM,11),fill=MUTED)
        d.text((gx+col_w-26,gy),"PTS",font=lfr(PM,11),fill=MUTED)
        ty=gy+18
        for ti,team in enumerate(grp['teams']):
            if ti<2: d.rectangle([gx+2,ty+2,gx+4,ty+16],fill=GOLD if ti==0 else ACCENT)
            nc=WHITE if ti<2 else MUTED
            d.text((gx+8,ty),team['name'][:12],font=f_gt,fill=nc)
            d.text((gx+col_w-86,ty),str(team.get('played',1)),font=f_gt,fill=MUTED)
            gd=team.get('gd','+0')
            gdc=GREEN if gd.startswith('+') else ((220,80,80) if gd.startswith('-') else MUTED)
            d.text((gx+col_w-58,ty),gd,font=f_gt,fill=gdc)
            pb=d.textbbox((0,0),str(team['pts']),font=f_gp); pw=pb[2]-pb[0]
            d.text((gx+col_w-8-pw,ty-4),str(team['pts']),font=f_gp,fill=GOLD if ti==0 else nc)
            ty+=19; max_rows=max(max_rows,ty-y)
        if col<cols-1:
            d.rectangle([gx+col_w-1,gy,gx+col_w,ty],fill=(25,40,75))
    y+=max_rows+12

    # Scorers
    y=sec_hdr(d,"GOLDEN BOOT RACE",y,S)
    sc_cw=(S-PAD*2)//3; rl=["1ST","2ND","3RD"]; rc=[(212,168,75),(160,168,185),(180,100,40)]
    f_sn=lfr(PB,19); f_ss=lfr(PM,14); f_sg=lfr(BEBAS_F,44)
    for si,sc in enumerate(scorers[:3]):
        sx=PAD+si*sc_cw+sc_cw//2
        rb_w=36; rb_x=sx-rb_w//2
        d.rounded_rectangle([rb_x,y,rb_x+rb_w,y+20],radius=4,fill=rc[si])
        rlb=d.textbbox((0,0),rl[si],font=lfr(PB,11)); rw=rlb[2]-rlb[0]
        d.text((sx-rw//2,y+3),rl[si],font=lfr(PB,11),fill=(10,10,20))
        gb=d.textbbox((0,0),str(sc['goals']),font=f_sg); gw=gb[2]-gb[0]
        d.text((sx-gw//2,y+24),str(sc['goals']),font=f_sg,fill=WHITE)
        nb=d.textbbox((0,0),sc['name'],font=f_sn); nw=nb[2]-nb[0]
        d.text((sx-nw//2,y+68),sc['name'],font=f_sn,fill=WHITE)
        tb=d.textbbox((0,0),sc['team'],font=f_ss); tw=tb[2]-tb[0]
        d.text((sx-tw//2,y+90),sc['team'],font=f_ss,fill=ACCENT)
    y+=112

    # Player of day
    y=sec_hdr(d,"PLAYER OF THE DAY",y,S)
    d.rounded_rectangle([PAD,y,S-PAD,y+84],radius=10,fill=(15,24,52))
    d.rectangle([PAD,y,PAD+5,y+84],fill=GOLD)
    cxr(d,stat_hero['name'].upper(),lfr(BEBAS_F,52),y+4,S,WHITE)
    cxr(d,stat_hero['team'],lfr(PM,16),y+56,S,ACCENT)
    cxr(d,stat_hero['stat'],lfr(PM,15),y+74,S,OFF_W)
    y+=96

    # Brand
    bar_y=y+10
    d.rectangle([0,bar_y,S,bar_y+48],fill=NAVY)
    d.rectangle([0,bar_y,S,bar_y+4],fill=GOLD_DK)
    cxr(d,"WORLD CUP IN 5  ·  2026  ·  @WORLDCUPIN5",lfr(PB,17),bar_y+14,S,WHITE)

    final_h=bar_y+48
    img=img.crop((0,0,S,final_h))
    if final_h<S:
        padded=Image.new("RGB",(S,S),(8,14,35))
        padded.paste(img,(0,(S-final_h)//2))
        img=padded

    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    safe_save(img, output_path)
    return output_path


def claude_recap_content(day_num, results, scorers_raw, standings_raw):
    """Ask Claude to pick player of the day and write recap caption."""
    results_txt = "\n".join([f"{r['home']} {r['score']} {r['away']}" for r in results])
    scorers_txt = ", ".join([f"{s['name']} ({s['team']}) {s['goals']} goals" for s in scorers_raw[:5]])
    prompt = (
        f"World Cup Day {day_num} just ended. Results:\n{results_txt}\n\n"
        f"Top scorers so far: {scorers_txt}\n\n"
        f"1. Pick the PLAYER OF THE DAY — one player who stood out most today. "
        f"Give their name, team, and a ONE line stat/story (max 12 words).\n"
        f"2. Write an Instagram end-of-day recap caption (max 120 words before hashtags). "
        f"Punchy, expert tone. End with a CTA to follow @worldcupin5.\n\n"
        f"Respond in this EXACT JSON format, no markdown:\n"
        f'{{"player_name":"","player_team":"","player_stat":"","caption":""}}'
    )
    result = claude_call(prompt, max_tokens=400)
    if not result:
        return None
    try:
        import json
        # strip any accidental markdown
        clean = result.strip().lstrip('`').rstrip('`')
        if clean.startswith('json'): clean=clean[4:]
        return json.loads(clean)
    except Exception as e:
        log.error(f"Recap JSON parse error: {e} — raw: {result[:200]}")
        return None


def recap_done_today():
    return (TMP_DIR / f"recap_{et_today().replace('-','')}.done").exists()

def mark_recap_done():
    (TMP_DIR / f"recap_{et_today().replace('-','')}.done").touch()


def job_recap_card():
    """Generate end-of-day recap card at midnight ET (04:00 UTC)."""
    try:
        if recap_done_today(): return

        today_et = et_now()
        date_str  = today_et.strftime("%A, %B %-d")
        dn        = day_number()

        # Get today's finished matches
        finished = [m for m in get_todays_matches() if m["status"] == "FINISHED"]
        if not finished:
            log.info("Recap job: no finished matches today, skipping")
            mark_recap_done(); return

        # Build results list
        results = []
        for m in finished:
            hs = m["score"]["fullTime"]["home"]
            as_ = m["score"]["fullTime"]["away"]
            home = m["homeTeam"]["name"]; away = m["awayTeam"]["name"]
            winner = home if hs > as_ else (away if as_ > hs else None)
            results.append({"home": home, "away": away,
                           "score": f"{hs}–{as_}", "winner": winner})

        # Get standings
        try:
            standings_data = fd_get(f"/competitions/WC/standings")
            raw_standings = standings_data.get("standings", [])
            standings = []
            for grp in raw_standings[:6]:  # max 6 groups on any day
                group_letter = grp.get("group","").replace("GROUP_","")
                if not group_letter: continue
                teams = []
                for row in grp.get("table", [])[:4]:
                    gd = row.get("goalDifference", 0)
                    teams.append({
                        "name": row["team"]["shortName"] or row["team"]["name"],
                        "pts":  row["points"],
                        "played": row["playedGames"],
                        "gd": f"+{gd}" if gd > 0 else str(gd)
                    })
                if teams:
                    standings.append({"group": group_letter, "teams": teams})
        except Exception as e:
            log.warning(f"Standings fetch failed: {e}")
            standings = [{"group":"?","teams":[{"name":"See standings","pts":0,"played":0,"gd":"0"}]}]

        # Get top scorers
        try:
            scorers_data = fd_get("/competitions/WC/scorers?limit=10")
            scorers_raw = [{"name": s["player"]["name"],
                           "team": s["team"]["shortName"] or s["team"]["name"],
                           "goals": s["goals"]}
                          for s in scorers_data.get("scorers", [])]
        except Exception as e:
            log.warning(f"Scorers fetch failed: {e}")
            scorers_raw = [{"name":"See golden boot","team":"","goals":0}]

        # Get Claude to pick player of day + write caption
        ai = claude_recap_content(dn, results, scorers_raw, standings)
        if ai:
            stat_hero = {"name": ai["player_name"],
                        "team": ai["player_team"],
                        "stat": ai["player_stat"]}
            caption_text = ai["caption"]
        else:
            # fallback
            stat_hero = {"name": results[0]['home'] if results else "—",
                        "team": "World Cup 2026",
                        "stat": "Standout performance today"}
            caption_text = f"Day {dn} is done. Follow @worldcupin5 for every result."

        # Build scorers for card (top 3)
        scorers_card = scorers_raw[:3] if scorers_raw else [
            {"name":"Golden Boot","team":"TBD","goals":0}]

        # Generate card
        img_path = str(TMP_DIR / f"recap_{et_today().replace('-','')}.png")
        make_recap_card(dn, date_str, results, standings, scorers_card, stat_hero, img_path)

        # Build full caption with hashtags
        hashtags = build_hashtag_block("","","group stage")
        full_caption = f"{caption_text}\n\n{hashtags}"

        fname = f"RECAP_{today_et.strftime('%Y%m%d')}_Day{dn}"
        upload_dropbox(img_path, f"{fname}.png")
        save_caption_file(full_caption, fname)
        mark_recap_done()
        log.info(f"Recap card posted for {date_str}")

    except Exception as e:
        log.error(f"Recap job error: {e}", exc_info=True)

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    log.info("World Cup in 5 — Poller v2 starting")
    download_fonts()
    schedule.every(5).minutes.do(job_result_cards)  # 5 min = 12 calls/hr, safe for free tier
    schedule.every().day.at("12:00").do(job_schedule_card)  # 8am ET = 12:00 UTC
    schedule.every().day.at("04:00").do(job_recap_card)     # midnight ET = 04:00 UTC
    log.info("Running initial jobs...")
    job_schedule_card()
    job_result_cards()
    # Run recap if not already done today (catches restarts after midnight)
    job_recap_card()
    log.info("Poller running.")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
