"""Original vector-style Cold Steel skill icon; no third-party image inputs."""
import math
from pathlib import Path
from PIL import Image, ImageDraw

P=Path(__file__).parent
S=1024
im=Image.new('RGBA',(S,S),(0,0,0,0));d=ImageDraw.Draw(im)
def hexagon(r):
    return [(512+math.cos(math.radians(30+60*i))*r,512+math.sin(math.radians(30+60*i))*r) for i in range(6)]
d.polygon(hexagon(491),fill=(80,83,85),outline=(202,205,206),width=7)
d.polygon(hexagon(473),fill=(157,161,164))
d.polygon(hexagon(451),fill=(38,41,43),outline=(211,214,215),width=3)
d.polygon(hexagon(430),fill=(24,26,28),outline=(8,10,11),width=9)
# Three engraved sweep arcs make the silhouette legible at hotbar size.
for box,start,end,width,color in [((177,254,849,776),-48,208,30,(79,84,88)),((193,270,833,760),-44,202,12,(210,217,221)),((252,331,772,699),-15,163,20,(142,151,157)),((294,384,730,642),190,340,12,(112,125,134))]:
    d.arc(box,start,end,fill=color,width=width)
d.polygon([(190,394),(175,325),(246,349)],fill=(218,224,228))
d.polygon([(818,622),(850,688),(774,679)],fill=(192,201,207))
# Horizontal sword: the two bright bevels meet at a dark fuller.
d.polygon([(337,492),(733,480),(820,512),(733,544),(337,532)],fill=(171,181,187),outline=(221,228,231),width=3)
d.polygon([(349,510),(737,503),(790,512),(734,519),(348,520)],fill=(52,65,75))
d.line([(351,494),(732,484),(807,511)],fill=(240,244,245),width=5)
d.rounded_rectangle((301,466,325,558),radius=7,fill=(179,183,185),outline=(227,230,231),width=4)
d.rounded_rectangle((227,498,302,526),radius=6,fill=(52,48,43),outline=(113,112,110),width=3)
for x in range(239,297,12):d.line([(x,500),(x-6,524)],fill=(151,144,132),width=3)
d.ellipse((211,496,239,529),fill=(148,157,161),outline=(214,218,219),width=3)
im=im.resize((512,512),Image.Resampling.LANCZOS)
im.save(P/'whirlwind_cold_steel.png')
im.save(P.parents[1]/'Content/ColdSteelData/Skills/whirlwind_cold_steel.png')
print('Created original whirlwind icon and runtime PNG.')
