"""Code-native editable relief, traced from the approved LeiMingConceptV2 design.

Builds PBR maps from authored vector ribbons, not from the concept's lighting.
All physical maps share one height field and one isotropic shaft projection.
"""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter, maximum_filter

P=Path(__file__).resolve().parent
P.mkdir(parents=True,exist_ok=True)
W,H=1024,4096
SS=3
S=1.45
layers=[]
svg=[]

def bez(a,b,c,d,n=100):
    t=np.linspace(0,1,n)[:,None]
    return ((1-t)**3*np.array(a)+3*(1-t)**2*t*np.array(b)+3*(1-t)*t*t*np.array(c)+t**3*np.array(d)).tolist()

def coord(points):
    return [((x-250)*S+512,(y-92)*S+850) for x,y in points]

def layer(points,width=None,holes=(),erase=False):
    layers.append((points,width,holes,erase))
    color='black' if erase else 'white'
    p=' '.join(f'{x:.3f},{y:.3f}' for x,y in points)
    if width:
        svg.append(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="miter" stroke-linecap="butt"/>')
    else:
        svg.append(f'<polygon points="{p}" fill="{color}"/>')
    for hole in holes:
        p=' '.join(f'{x:.3f},{y:.3f}' for x,y in hole)
        svg.append(f'<polygon points="{p}" fill="black"/>')

def ribbon_pair(a,b,width,cross_indices):
    # First draw both strands. Re-cut only the crossing windows so the order
    # alternates, leaving actual separation instead of merged flat intersections.
    layer(a,width);layer(b,width)
    for order,index in enumerate(cross_indices):
        over=a if order%2==0 else b
        segment=over[max(0,index-9):min(len(over),index+10)]
        layer(segment,width+5,erase=True)
        layer(segment,width)

# Both flanks: angular shoulders, continuous enclosing curves, open woven bands.
for side in (-1,1):
    def mirror(points):return [(250+side*(250-x),y) for x,y in points]
    outer=bez((200,225),(153,228),(106,253),(105,302))
    outer+=bez((105,302),(100,350),(162,389),(177,429))
    outer+=bez((177,429),(198,466),(171,491),(145,513))
    layer(mirror(outer),9)
    layer(mirror([(163,214),(179,188),(202,215),(183,222)]),9)
    a=[];b=[]
    for t in np.linspace(0,1,301):
        y=239+t*265
        center=149+18*math.sin(t*math.pi*2-.2)
        span=28*math.sin(math.pi*t)**.65
        wave=span*math.sin(t*math.pi*3)
        a.append((center+wave,y));b.append((center-wave,y))
    ribbon_pair(mirror(a),mirror(b),8,[100,200])
    layer(mirror([(145,505),(165,523),(155,536),(144,526),(150,518)]),8)
    # Tapered inner arm, separated from the main lightning stroke.
    inner=bez((192,240),(187,281),(185,310),(205,336))
    layer(mirror(inner),6)

# Lightning spine: a shaped, faceted ribbon rather than a uniform round stroke.
spine=[(256,169),(276,159),(251,220),(198,356),(276,334),
       (235,408),(207,474),(192,503),(180,527),(202,441),
       (243,365),(174,385),(214,284),(240,208)]
layer(spine)
layer([(254,96),(288,153),(255,195),(215,155)],holes=[[(254,123),(270,153),(254,176),(235,154)]])
layer([(250,135),(259,154),(250,165),(242,154)])
layer([(208,404),(221,418),(204,441),(190,426)],holes=[[(207,416),(211,420),(204,430),(200,426)]])
layer([(250,496),(282,532),(252,577),(218,532)],holes=[[(250,515),(264,533),(252,553),(236,533)]])
layer([(251,521),(258,533),(251,545),(244,533)])

# The two-strand tail is part of the approved silhouette, not repeated filler.
a=[];b=[]
for t in np.linspace(0,1,501):
    y=568+t*238
    width=26*(.92-.34*t)
    x=width*math.sin(t*math.pi*4)
    a.append((251+x,y));b.append((251-x,y))
ribbon_pair(a,b,10,[125,250,375])
layer([(251,787),(278,832),(251,900),(225,832)],holes=[[(251,815),(263,834),(251,874),(239,834)]])

# Render only the authored geometry to a compact working canvas with oversampling.
# The rest of the 4K shaft sheet stays empty; no stretching to fill the whole grip.
im=Image.new('L',(W*SS,H*SS));draw=ImageDraw.Draw(im)
for pts,width,holes,erase in layers:
    xy=[(round(x*SS),round(y*SS)) for x,y in coord(pts)]
    if width:
        draw.line(xy,fill=0 if erase else 255,width=max(1,round(width*S*SS)),joint='curve')
    else:draw.polygon(xy,fill=0 if erase else 255)
    for hole in holes:draw.polygon([(round(x*SS),round(y*SS)) for x,y in coord(hole)],fill=0)
mask=np.asarray(im.resize((W,H),Image.Resampling.LANCZOS),dtype=np.float32)/255
inside=mask>.5
dist=distance_transform_edt(inside).astype(np.float32)
outside=distance_transform_edt(~inside).astype(np.float32)
bevel=np.clip(dist/2.5,0,1)
channel=np.clip((dist-3.0)/1.8,0,1)*mask
# Physical height in cm: 0.35 mm rims, shallow chased centre channel.
height=(.035*bevel-.013*channel)*mask
y,x=np.mgrid[0:H,0:W].astype(np.float32)
# Fine deterministic tool facets; amplitude < 0.012 mm, no fake baked highlights.
chase=(np.sin(x*1.16+y*.39)*np.sin(x*.21-y*.83))*.0011
height+=chase*mask*np.clip((dist-1)/2,0,1)
height=gaussian_filter(height,.42)
cm_per_px=33.5/H
dy,dx=np.gradient(height,cm_per_px)
n=np.dstack((-dx,dy,np.ones_like(height)))
n/=np.linalg.norm(n,axis=2,keepdims=True)
coverage=np.maximum(mask,np.clip(1-outside/1.5,0,1)*.76)
rough=np.clip(.30+.13*channel+.055*(1-bevel)+.012*np.sin(x*.22+y*.1),0,1)
tone=np.clip(.81-.47*channel+.1*bevel,0,1)
ao=np.clip(1-.25*channel-.32*(coverage-mask),0,1)
metal=mask*.94
packed=np.dstack((coverage,channel*.94,mask))
surface=np.dstack((rough,tone,metal,ao))
def png(name,data):Image.fromarray(np.uint8(np.clip(data,0,1)*255+.5)).save(P/name)
png('T_Mask_lei_ming_rune.png',packed)
png('T_Normal_lei_ming_rune.png',n*.5+.5)
png('T_Roughness_lei_ming_rune.png',surface)
Image.fromarray(np.uint16(np.clip(height/.04,0,1)*65535)).save(P/'T_Height_lei_ming_rune.png')
# Editable design uses the same path list as all baked production maps.
(P/'lei_ming_rune_refined.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="80 80 340 840"><rect x="80" y="80" width="340" height="840" fill="black"/>'+''.join(svg)+'</svg>',encoding='utf-8')
meta=dict(approved_design='../LeiMingConceptV2/lei_ming_rune_design_v2.png',
    source='Editable code-native ribbon paths and physical relief height field',
    texture_size=[W,H],normal='DirectX',height_cm=.035,height_bits=16,
    mask_channels={'R':'stable engraved coverage','G':'recessed electric channels','B':'silver inlay'},
    surface_channels={'R':'roughness','G':'silver tone','B':'metallic','A':'micro occlusion'},
    shaft_height_cm=33.5,shaft_start_cm=-35.5,isotropic_art_scale=True,
    motif_height_cm=(900-96)*S*cm_per_px,motif_width_cm=290*S*cm_per_px,
    crossing_order='alternating over-under, separated 5px in design coordinates',runtime_tested=False)
(P/'author_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print('LEIMING_REFINED_MAPS_AUTHORED',flush=True)
