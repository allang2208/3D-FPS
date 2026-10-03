"""Original labels and dimension drawings used as authoring sources, never stretched."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
for folder in ('Config','Receipts'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
labels=[('检修工具','MAINTENANCE TOOLS'),('防护用品','PROTECTIVE EQUIPMENT'),('耐热器材','HEAT SERVICE EQUIPMENT'),
        ('停尸档案','MORTUARY RECORDS'),('滤芯备件','FILTER CARTRIDGES')]
image=Image.new('RGB',(800,2000),(216,213,192));draw=ImageDraw.Draw(image)
cn_font=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',62)
en_font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',26)
for row,(cn,en) in enumerate(labels):
    y=row*400
    draw.rectangle((18,y+18,781,y+381),outline=(55,66,59),width=5)
    draw.rectangle((22,y+22,777,y+77),fill=(55,66,59))
    draw.text((52,y+116),cn,font=cn_font,fill=(37,45,39))
    draw.text((54,y+224),en,font=en_font,fill=(57,63,53))
    draw.line((52,y+282,748,y+282),fill=(97,98,78),width=2)
    draw.text((54,y+315),'TREATMENT / '+str(row+1).zfill(2)+'  |  SERVICE STOCK',font=en_font,fill=(64,69,58))
image.save(OUT/'T_Treatment_Labels.png')
design=[dict(id='ToolBox',caption='检修工具箱',dimensions_cm=[70,36,32],opening='Lid',
             details=['folded shell','removable tray','hand tools','rear hinge','latches']),
        dict(id='PPELocker',caption='防护用品柜',dimensions_cm=[64,43,170],opening='Swing',
             details=['vent gaps','fixed shelves','protection packs','respirators','lock']),
        dict(id='HeatCabinet',caption='耐热器材柜',dimensions_cm=[80,49,108],opening='Swing + Drawer',
             details=['ceramic door lining','ceramic handle','runner frame','independent upper tray']),
        dict(id='RecordsCabinet',caption='停尸间档案柜',dimensions_cm=[74,46,116],opening='3 independent drawers',
             details=['reusable runner frames','file folders','label frames','three searches']),
        dict(id='FilterCase',caption='滤芯运输箱',dimensions_cm=[64,42,36],opening='Lid',
             details=['rubber seal','pleated cartridges','hollow sleeve','end caps','cradle rails'])]
(ROOT/'Config/design.json').write_text(json.dumps(dict(families=design,label_panel_pixels=[800,400],
    label_width_height_ratio=2,label_policy='native font drawing, equal physical and UV aspect, no image resize',
    scope='models and saved UE assets; room placement is separate',tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
# Editable orthographic construction drawings; not beauty renders or acceptance captures.
drawings=OUT/'Drawings';drawings.mkdir(exist_ok=True)
for item in design:
    w,d,h=item['dimensions_cm'];scale=min(3.0,280/max(w,d,h))
    shapes=[]
    for caption,x,y,width,height in [('FRONT',40,80,w,h),('SIDE',340,80,d,h),('TOP',630,80,w,d)]:
        ww,hh=width*scale,height*scale
        shapes.append(f'<text x="{x}" y="{y-15}" font-size="16">{caption}: {width} x {height} cm</text>'
                      f'<rect x="{x}" y="{y}" width="{ww}" height="{hh}" fill="none" stroke="#354139" stroke-width="2"/>')
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="430" viewBox="0 0 1000 430"><rect width="1000" height="430" fill="#eeeade"/><g font-family="Consolas,monospace" fill="#26352a">'+f'<text x="40" y="35" font-size="20">{item["id"]} | body dimensions | {item["opening"]}</text>'+''.join(shapes)+'</g></svg>'
    (drawings/(item['id']+'.svg')).write_text(svg,encoding='utf8')
print('TREATMENT_LABELS_AND_DESIGN_AUTHORED',flush=True)
