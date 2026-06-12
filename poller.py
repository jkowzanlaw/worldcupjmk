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
def fd_get(path):
    r = requests.get(f"https://api.football-data.org/v4{path}",
                     headers={"X-Auth-Token": FD_KEY}, timeout=15)
    r.raise_for_status()
    return r.json()

def get_todays_matches():
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return fd_get(f"/competitions/WC/matches?dateFrom={date_str}&dateTo={date_str}").get("matches", [])

def format_kickoff_et(utc_str):
    """Convert UTC kickoff time to US Eastern Time (EDT = UTC-4)."""
    dt = datetime.fromisoformat(utc_str.replace("Z","+00:00"))
    et = dt - timedelta(hours=4)  # EDT summer offset
    hour24 = et.hour
    hour12 = hour24 % 12 or 12
    ampm = "AM" if hour24 < 12 else "PM"
    mins = et.strftime('%M')
    return f"{hour12}:{mins} {ampm} ET"

def match_stage_label(match):
    stage = match.get("stage","").replace("_"," ").title()
    group = match.get("group","")
    if group: return f"{stage} · {group.replace('GROUP_','Group ')}"
    return stage

def day_number():
    return max(1, (datetime.now(timezone.utc) - TOURNAMENT_START).days + 1)

# ── Dropbox ───────────────────────────────────────────────────────────────────
def upload_dropbox(local_path, filename):
    dbx = dropbox.Dropbox(DBX_TOKEN)
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
    if POSTED_FILE.exists(): return set(json.loads(POSTED_FILE.read_text()))
    return set()

def save_posted(posted): POSTED_FILE.write_text(json.dumps(list(posted)))

def schedule_done_today():
    return (TMP_DIR / f"sched_{datetime.now(timezone.utc).strftime('%Y%m%d')}.done").exists()

def mark_schedule_done():
    (TMP_DIR / f"sched_{datetime.now(timezone.utc).strftime('%Y%m%d')}.done").touch()

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
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    img.save(output_path,"PNG")
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
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    img.save(output_path,"PNG")
    return output_path

# ── Core jobs ─────────────────────────────────────────────────────────────────
def job_result_cards():
    try:
        posted = load_posted()
        finished = [m for m in get_todays_matches() if m["status"]=="FINISHED"]
        new = [m for m in finished if str(m["id"]) not in posted]
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

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    log.info("World Cup in 5 — Poller v2 starting")
    download_fonts()
    schedule.every(3).minutes.do(job_result_cards)
    schedule.every().day.at("12:00").do(job_schedule_card)  # 8am ET = 12:00 UTC
    log.info("Running initial jobs...")
    job_schedule_card()
    job_result_cards()
    log.info("Poller running.")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
