"""Author new vector rune designs and their engine masks; no source-image editing."""
from pathlib import Path
from PIL import Image,ImageDraw
import json
P=Path(__file__).resolve().parent
OUT=P/'Masks';OUT.mkdir(exist_ok=True)

swift=[([(0,-360),(110,-70),(0,210),(-110,-70)],True),
       ([(-280,-235),(-240,-115),(-130,-55),(-78,130),(-174,-15),(-265,-70)],False),
       ([(-285,-100),(-230,30),(-155,80),(-80,190),(-205,110)],False),
       ([(-45,220),(-130,390),(-95,275)],False),
       ([(-10,245),(10,245),(18,375),(0,430),(-18,375)],False)]
swift += [([(-x,y) for x,y in poly],hole) for poly,hole in swift[1:4]]
destruction=[([(-10,-360),(-100,-125),(-40,-20),(10,-130),(35,-100)],False),
             ([(15,-360),(110,-120),(155,-25),(28,25),(-15,-30),(30,-120)],False),
             ([(-120,-75),(-175,35),(-60,205),(-12,90),(-60,35)],False),
             ([(30,60),(145,-5),(60,220),(10,155),(-18,112)],False),
             ([(-50,235),(15,175),(65,245),(0,380)],False),
             ([(-245,-250),(-160,-210),(-120,-120),(-200,-185)],False),
             ([(-250,300),(-150,255),(-108,180),(-210,240)],False),
             ([(-185,-130),(-270,-95),(-335,25),(-270,155),(-160,220),(-195,165),(-270,110),(-282,45),(-250,20),(-295,10),(-235,-70)],False)]
destruction += [([(-x,y) for x,y in poly],hole) for poly,hole in destruction[5:]]
receipt={'placement':'Existing shaft-local 33.5 cm wrap; 42.5 to 76 cm weapon height','designs':{}}
for name,polygons in [('swift_mana_rune',swift),('destruction_mana_rune',destruction)]:
    im=Image.new('L',(1024,4096),0);d=ImageDraw.Draw(im)
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="4096" viewBox="0 0 1024 4096"><rect width="1024" height="4096" fill="black"/>']
    def polygon(points,fill=255):
        d.polygon(points,fill=fill)
        svg.append('<polygon fill="'+('white' if fill else 'black')+'" points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in points)+'"/>')
    for center,scale in [(900,.60),(2048,.83),(3190,.60)]:
        for shape,hole in polygons:
            polygon([(512+x*scale,center+y*scale) for x,y in shape])
            if hole:
                polygon([(512+x*scale*.53,center+(y+65)*scale*.60-65*scale) for x,y in shape],0)
    for low,high in [(285,640),(1200,1700),(2440,2910),(3470,3810)]:
        polygon([(500,low+35),(512,low),(524,low+35),(521,high-25),(512,high),(503,high-25)])
        y=(low+high)/2
        for sign in (-1,1):
            polygon([(512+sign*46,y-70),(512+sign*62,y-45),(512+sign*62,y+45),(512+sign*46,y+70)])
    svg.append('</svg>')
    (OUT/(name+'.svg')).write_text('\n'.join(svg),encoding='utf-8')
    im.save(OUT/('T_Mask_'+name+'.png'))
    receipt['designs'][name]={'vector':name+'.svg','texture':'T_Mask_'+name+'.png','size':[1024,4096],'symbol_centres_px':[900,2048,3190]}
(P/'mask_authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('Two vector rune masks authored')
