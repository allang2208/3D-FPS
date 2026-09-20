"""Lay out the two actual model renders; no generated or retouched geometry."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parents[1]/'Revisions/PalmGripV3'
sheet=Image.new('RGB',(1280,736),(25,31,38));draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
for x,folder,title in [(0,'BeforeRender','调整前：手指张开'),(640,'DeliveryRender','调整后：并拢、弯指包握')]:
 sheet.paste(Image.open(O/folder/'front.jpg').convert('RGB'),(x,52))
 draw.text((x+22,12),title,font=font,fill=(230,237,245))
draw.text((22,703),'实际蒙皮模型姿态预览 · 保留掌心托底 · 非游戏截图',font=small,fill=(169,184,199))
sheet.save(O/'palm-grip-before-after.jpg',quality=88)
print(O/'palm-grip-before-after.jpg')
