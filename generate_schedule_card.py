#!/usr/bin/env python3
"""
World Cup in 5 — Daily Schedule Card Generator (Production)
1080x1080 Instagram-ready. Rows fill the canvas regardless of match count.
Matches visual identity of result cards (gold/navy vs team-color result cards).

Usage:
    from generate_schedule_card import generate_schedule_card

    generate_schedule_card(
        matches=[
            {"time":"9:00 AM ET","home":"USA","away":"Paraguay","group":"Group D","stage":"Group Stage"},
            {"time":"3:00 PM ET","home":"Brazil","away":"Croatia","group":"Group E","stage":"Group Stage"},
        ],
        date_str="Thursday, June 12",
        day_number=2,
        output_path="schedule_june12.png"
    )
"""

from PIL import Image, ImageDraw, ImageFont
import os

BEBAS     = "/tmp/BebasNeue.ttf"
POPPINS_B = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
POPPINS_R = "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf"
POPPINS_M = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"

def lf(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

def cx(d, text, font, y, W, color):
    bb=d.textbbox((0,0),text,font=font); w=bb[2]-bb[0]; x=(W-w)//2
    d.text((x,y),text,font=font,fill=color)

def generate_schedule_card(matches, date_str, day_number, output_path="schedule.png"):
    S=1080
    img=Image.new("RGB",(S,S),"#FFFFFF"); d=ImageDraw.Draw(img)
    NAVY=(10,18,45); GOLD=(212,168,75); GOLD_LT=(240,215,140)
    GOLD_DK=(160,122,40); OFF_W=(252,250,245); MID=(28,42,80)
    MUTED=(120,130,155); WHITE=(255,255,255)

    # Header zone
    d.rectangle([0,0,S,290],fill=NAVY)
    for i in range(0,80,8): d.line([(0,180+i),(120+i,60)],fill=(30,48,100),width=1)
    d.rectangle([0,290,S,300],fill=GOLD)
    d.rectangle([0,300,S,S],fill=OFF_W)

    # Header text
    f_ey=lf(POPPINS_B,22); f_dy=lf(BEBAS,130); f_dt=lf(POPPINS_B,32)
    f_sh=lf(POPPINS_M,22); f_br=lf(POPPINS_B,21)
    cx(d,"2026 FIFA WORLD CUP  ·  TODAY'S MATCHES",f_ey,28,S,GOLD)
    cx(d,f"DAY {day_number}",f_dy,52,S,WHITE)
    cx(d,date_str.upper(),f_dt,188,S,GOLD_LT)
    mc=f"{len(matches)} MATCH{'ES' if len(matches)!=1 else ''} TODAY"
    mcbb=d.textbbox((0,0),mc,font=f_sh); mcw=mcbb[2]-mcbb[0]+36; mcx=(S-mcw)//2
    d.rounded_rectangle([mcx,232,mcx+mcw,272],radius=6,fill=MID)
    cx(d,mc,f_sh,238,S,GOLD_LT)

    # Match rows — fill body zone completely
    n=len(matches); pad_x=48; FOOTER=80
    body_top=300; body_bot=S-FOOTER; body_h=body_bot-body_top
    row_h=(body_h-24)//n; start_y=body_top+12

    # Font scale by row height
    if row_h>=180:   tf=lf(BEBAS,78);  tif=lf(POPPINS_B,30); gf=lf(POPPINS_M,23)
    elif row_h>=130: tf=lf(BEBAS,62);  tif=lf(POPPINS_B,26); gf=lf(POPPINS_M,20)
    elif row_h>=100: tf=lf(BEBAS,52);  tif=lf(POPPINS_B,22); gf=lf(POPPINS_M,17)
    else:            tf=lf(BEBAS,44);  tif=lf(POPPINS_B,18); gf=lf(POPPINS_M,15)

    for i,m in enumerate(matches):
        y=start_y+i*row_h; ym=y+row_h//2
        d.rectangle([pad_x,y+4,S-pad_x,y+row_h-4],fill=(244,242,238) if i%2==0 else WHITE)
        d.rectangle([pad_x,y+4,pad_x+5,y+row_h-4],fill=GOLD)
        tb=d.textbbox((0,0),m["time"],font=tif); th=tb[3]-tb[1]
        d.text((pad_x+18,ym-th//2-8),m["time"],font=tif,fill=NAVY)
        if m.get("group"):
            d.text((pad_x+18,ym+6),m["group"],font=gf,fill=MUTED)
        tc=(pad_x+190+(S-pad_x))//2
        hu=m["home"].upper(); au=m["away"].upper()
        hb=d.textbbox((0,0),hu,font=tf); ab=d.textbbox((0,0),au,font=tf)
        hw=hb[2]-hb[0]; aw=ab[2]-ab[0]
        vb=d.textbbox((0,0),"vs",font=gf); vw=vb[2]-vb[0]
        g2=16; tw=hw+g2+vw+g2+aw; tx=tc-tw//2
        ty2=ym-(hb[3]-hb[1])//2-4
        d.text((tx,ty2),hu,font=tf,fill=NAVY)
        d.text((tx+hw+g2,ym-(vb[3]-vb[1])//2),"vs",font=gf,fill=MUTED)
        d.text((tx+hw+g2+vw+g2,ty2),au,font=tf,fill=NAVY)
        st=m.get("stage","").upper()
        if st:
            sb=d.textbbox((0,0),st,font=gf); sw=sb[2]-sb[0]
            d.text((S-pad_x-sw-8,ym-(sb[3]-sb[1])//2),st,font=gf,fill=GOLD_DK)
        if i<n-1:
            d.rectangle([pad_x+5,y+row_h-1,S-pad_x,y+row_h],fill=(220,218,212))

    # note absorbed into brand bar
    d.rectangle([0,S-56,S,S],fill=NAVY); d.rectangle([0,S-56,S,S-52],fill=GOLD_DK)
    cx(d,"WORLD CUP IN 5  ·  2026  ·  ALL TIMES ET",f_br,S-38,S,WHITE)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)),exist_ok=True)
    img.save(output_path,"PNG")
    return output_path
