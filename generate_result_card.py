#!/usr/bin/env python3
"""
World Cup in 5 — Result Card (Production)
1080x1080 Instagram-ready. Field background top half, white bottom.

Usage:
    from generate_result_card import generate_result_card
    generate_result_card(
        home_team="USA", away_team="Paraguay",
        home_score=2, away_score=0,
        stage="Group Stage · Group D",
        venue="SoFi Stadium · Los Angeles",
        insight="Pulisic opens in the 23rd. USA controlled every minute.",
        match_date="June 12, 2026",
        stats={"labels":["POSS","SHOTS"],"home":["58%","9"],"away":["42%","4"]},
        output_path="result.png"
    )
"""

from PIL import Image, ImageDraw, ImageFont
import os

BEBAS     = "/tmp/BebasNeue.ttf"
POPPINS_B = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
POPPINS_R = "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf"
POPPINS_M = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"

PITCH_DARK = (34, 80, 18)
PITCH_MID  = (44, 100, 24)
PITCH_EDGE = (22, 55, 10)

TEAM_COLORS = {
    "Argentina":"#74ACDF","Brazil":"#009C3B","France":"#002395",
    "England":"#CF142B","Spain":"#AA151B","Germany":"#222222",
    "Portugal":"#006600","USA":"#B22234","Mexico":"#006847",
    "Canada":"#D80621","Morocco":"#C1272D","Japan":"#BC002D",
    "Netherlands":"#E77728","Uruguay":"#5EB6E4","Senegal":"#00853F",
    "Croatia":"#D4263D","Colombia":"#C8A84B","Nigeria":"#008751",
    "Australia":"#C8A84B","Turkey":"#E30A17","South Korea":"#CD2E3A",
    "Iran":"#239F40","Poland":"#DC143C","Ecuador":"#C8A84B",
    "Paraguay":"#D52B1E","Switzerland":"#D52B1E","Denmark":"#C60C30",
    "Serbia":"#C6363C","South Africa":"#007A4D","Bosnia":"#002F6C",
    "Saudi Arabia":"#006C35","Ghana":"#006B3F",
}

def lf(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

def get_accent(name):
    for k,v in TEAM_COLORS.items():
        if k.lower() in name.lower(): return v
    return "#1a5c2a"

def hr(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def darken(h,f=0.62):  r,g,b=hr(h); return (int(r*f),int(g*f),int(b*f))

def centered(d, text, font, y, W, color, shadow=None):
    bb=d.textbbox((0,0),text,font=font); w=bb[2]-bb[0]; x=(W-w)//2
    if shadow: d.text((x+3,y+3),text,font=font,fill=shadow)
    d.text((x,y),text,font=font,fill=color)

def col_text(d, text, font, y, cx_pos, color):
    bb=d.textbbox((0,0),text,font=font); w=bb[2]-bb[0]
    d.text((cx_pos-w//2,y),text,font=font,fill=color)

def wrap_text(d, text, font, max_w):
    words=text.split(); lines=[]; line=[]
    for w in words:
        test=" ".join(line+[w])
        if d.textbbox((0,0),test,font=font)[2]>max_w:
            if line: lines.append(" ".join(line))
            line=[w]
        else: line.append(w)
    if line: lines.append(" ".join(line))
    return lines

def draw_pitch(d, S, top_h):
    # Vertical mow stripes
    stripe_w = 54
    for x in range(0, S, stripe_w*2):
        d.rectangle([x,0,min(x+stripe_w,S),top_h], fill=PITCH_DARK)
        d.rectangle([min(x+stripe_w,S),0,min(x+stripe_w*2,S),top_h], fill=PITCH_MID)
    # Vignette border
    for i in range(22):
        darkness = int(80*(1-i/22))
        d.rectangle([i,i,S-i,top_h-i], outline=(0,0,0,darkness), width=1)
    # Center circle — positioned in upper half of field zone so score sits inside it
    cxp, cyp = S//2, int(top_h * 0.52)
    r = 175
    for t in range(3):
        d.ellipse([cxp-r+t,cyp-r+t,cxp+r-t,cyp+r-t],
                  outline=(255,255,255,28), width=1)
    # Center spot
    d.ellipse([cxp-4,cyp-4,cxp+4,cyp+4], fill=(255,255,255,40))
    # Halfway line
    d.rectangle([0,top_h//2,S,top_h//2+1], fill=(255,255,255,20))


def generate_result_card(
    home_team, away_team, home_score, away_score,
    stage, venue, insight, match_date,
    stats=None, output_path="match.png"
):
    S=1080; SPLIT=555; WHITE=(255,255,255); INK=(12,12,22)
    img=Image.new("RGB",(S,S),"#FFFFFF"); d=ImageDraw.Draw(img)

    won = home_team if home_score>away_score else (away_team if away_score>home_score else None)
    ax  = get_accent(won) if won else "#1a5c2a"
    ac  = hr(ax)
    adk = darken(ax, 0.62)

    # Field + white zones
    draw_pitch(d, S, SPLIT)
    d.rectangle([0,SPLIT,S,S], fill=(252,252,252))
    d.rectangle([0,SPLIT,S,SPLIT+8], fill=ac)

    # Fonts
    f_stg=lf(POPPINS_B,26); f_tm=lf(BEBAS,96); f_sc=lf(BEBAS,260)
    f_bdg=lf(POPPINS_B,29); f_ins=lf(POPPINS_B,37)
    f_sv=lf(BEBAS,48);      f_sl=lf(POPPINS_M,20)
    f_ven=lf(POPPINS_R,23); f_br=lf(POPPINS_B,21)

    # Stage label
    centered(d, stage.upper(), f_stg, 28, S, (205,230,205))

    # Result badge
    if   home_score>away_score: badge=f"{home_team.upper()} WIN"
    elif away_score>home_score: badge=f"{away_team.upper()} WIN"
    else:                        badge="DRAW"
    bb=d.textbbox((0,0),badge,font=f_bdg); bw=bb[2]-bb[0]+44
    bx=(S-bw)//2
    d.rounded_rectangle([bx,68,bx+bw,112],radius=7,fill=ac)
    centered(d,badge,f_bdg,76,S,WHITE)

    # Team names
    HL,HR=S//4,S*3//4; ty=130
    for name,ccx in [(home_team.upper(),HL),(away_team.upper(),HR)]:
        nbb=d.textbbox((0,0),name,font=f_tm); nw=nbb[2]-nbb[0]
        d.text((ccx-nw//2+3,ty+3),name,font=f_tm,fill=(0,0,0,90))
        d.text((ccx-nw//2,ty),name,font=f_tm,fill=WHITE)
    for ccx in [HL,HR]:
        d.rectangle([ccx-26,ty+98,ccx+26,ty+103],fill=ac)

    # Score — centered vertically in field zone below team names
    sc=f"{home_score}  –  {away_score}"
    scbb=d.textbbox((0,0),sc,font=f_sc); scw=scbb[2]-scbb[0]
    scx=(S-scw)//2
    # Position score to sit inside the center circle (circle center at ~52% of SPLIT)
    scy = int(SPLIT * 0.52) - (scbb[3]-scbb[1])//2 + 20
    d.text((scx+5,scy+5),sc,font=f_sc,fill=(0,0,0,100))
    d.text((scx,scy),sc,font=f_sc,fill=WHITE)

    # Insight
    lines=wrap_text(d,insight,f_ins,S-100)
    iy=SPLIT+28
    for i,ln in enumerate(lines[:3]):
        centered(d,ln,f_ins,iy+i*52,S,INK)
    iy_end=iy+len(lines[:3])*52

    # Stats row
    sy=iy_end+20
    if stats and stats.get("labels"):
        labels=stats["labels"]; hvals=stats.get("home",[]); avals=stats.get("away",[])
        n=len(labels); positions=[int(S*(i+1)/(n+1)) for i in range(n)]
        col_block=min(160,(S-80)//n)
        for i,(lbl,pos) in enumerate(zip(labels,positions)):
            hv=str(hvals[i]) if i<len(hvals) else "—"
            av=str(avals[i]) if i<len(avals) else "—"
            hvbb=d.textbbox((0,0),hv,font=f_sv); hvw=hvbb[2]-hvbb[0]
            d.text((pos-col_block//2-hvw//2,sy),hv,font=f_sv,fill=ac)
            col_text(d,lbl.upper(),f_sl,sy+10,pos,(150,150,158))
            avbb=d.textbbox((0,0),av,font=f_sv); avw=avbb[2]-avbb[0]
            d.text((pos+col_block//2-avw//2,sy),av,font=f_sv,fill=(80,80,90))
        for pos in positions[:-1]:
            sep=pos+col_block//2+8
            d.rectangle([sep,sy+4,sep+1,sy+46],fill=(210,210,215))
        sy+=62

    # Venue/date
    vy=max(sy+20,868)
    centered(d,venue.upper(),f_ven,vy,S,(145,145,152))
    centered(d,match_date,f_ven,vy+32,S,(160,160,168))

    # Brand bar
    d.rectangle([0,S-62,S,S],fill=PITCH_DARK)
    d.rectangle([0,S-62,S,S-58],fill=PITCH_EDGE)
    centered(d,"WORLD CUP IN 5  ·  2026",f_br,S-44,S,WHITE)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)),exist_ok=True)
    img.save(output_path,"PNG")
    print(f"✓ {output_path}")
    return output_path


if __name__=="__main__":
    generate_result_card(
        "USA","Paraguay",2,0,
        "Group Stage · Group D","SoFi Stadium · Los Angeles",
        "Pulisic opens in the 23rd. USA controlled every minute — clean sheet.",
        "June 12, 2026",
        output_path="/mnt/user-data/outputs/result_usa_paraguay.png"
    )
    generate_result_card(
        "Brazil","Colombia",3,3,
        "Group Stage · Group F","MetLife Stadium · New York / New Jersey",
        "Six goals, two red cards, last-minute equalizer. This group is chaos.",
        "June 14, 2026",
        stats={"labels":["POSS","SHOTS","SAVES"],"home":["58%","14","4"],"away":["42%","9","7"]},
        output_path="/mnt/user-data/outputs/result_brazil_colombia.png"
    )
    generate_result_card(
        "Morocco","France",1,0,
        "Round of 16","AT&T Stadium · Dallas",
        "Mbappé was invisible. The Atlas Lions are writing history again.",
        "July 5, 2026",
        stats={"labels":["POSS","SHOTS","CORNERS"],"home":["38%","6","3"],"away":["62%","18","9"]},
        output_path="/mnt/user-data/outputs/result_morocco_france.png"
    )
