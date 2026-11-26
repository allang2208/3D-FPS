"""Lay out matched orthographic views of the two posterior helmet silhouettes."""
from PIL import Image, ImageDraw, ImageFont
from helmet_nape_review import REVIEW


def assemble(rigs,width,output):
    height=round(width*492/496)
    side,top,gap=131,48,4
    names=(("side","侧面"),("oblique","后侧面"),("rear","背面"))
    sheet=Image.new("RGB",(side+3*(width+gap)+gap,top+len(rigs)*2*(height+gap)+gap),(30,33,37))
    label=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",20)
    small=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",17)
    draw=ImageDraw.Draw(sheet)
    for j,(_,name) in enumerate(names):
        draw.text((side+(width+gap)*j+width*.5,top*.5),name,anchor="mm",font=label,fill=(227,227,225))
    for i,rig in enumerate(rigs):
        for k,rev in enumerate(("R2","R3")):
            y=top+(2*i+k)*(height+gap)
            for j,(view,_) in enumerate(names):
                im=Image.open(REVIEW/f"{rig}-{rev}-{view}.png").convert("RGBA").resize((width,height),Image.Resampling.LANCZOS)
                bg=Image.new("RGBA",im.size,(62,65,68,255))
                bg.alpha_composite(im)
                sheet.paste(bg.convert("RGB"),(side+j*(width+gap),y))
            draw.text((13,y+height*.46),rig,font=label,fill=(236,233,227))
            draw.text((13,y+height*.46+31),f"{rev}  "+("原版" if k==0 else "后缘加深"),font=small,fill=(201,209,202))
    sheet.save(REVIEW/output,quality=92,optimize=True)


if __name__=="__main__":
    for rig in ("Jason","Kaitlin"):
        assemble([rig],430,f"{rig}-rear-comparison.jpg")
    assemble(["Jason","Kaitlin"],307,"rear-comparison.jpg")
