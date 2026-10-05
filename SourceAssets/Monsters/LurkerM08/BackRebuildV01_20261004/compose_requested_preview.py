from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
root=Path(r"D:\FPS3D\FPSGAME\SourceAssets\Monsters\LurkerM08\BackRebuildV01_20261004\PreviewRequested")
font=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc",32)
small=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc",22)
panel_w,panel_h=1400,1064
sheet=Image.new("RGB",(2800,2200),(31,35,40))
draw=ImageDraw.Draw(sheet)
draw.text((28,20),"M-08 伏窥者 · 背部重做 V01 · 实际 GLB 渲染",font=font,fill=(237,241,245))
for i,(file,label) in enumerate([("front","正面"),("side","侧面"),("back","背面"),("angle","斜视")]):
    x=(i%2)*panel_w;y=72+(i//2)*panel_h
    draw.text((x+24,y+14),label,font=font,fill=(235,238,242))
    with Image.open(root/(file+".png")) as im:sheet.paste(im.convert("RGB"),(x,y+64))
sheet.save(root/"M08_back_rebuild_v01_views.png")
