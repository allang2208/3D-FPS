"""Author the fitted bellows, charcoal bunker and hearth dressing in house-local centimetres."""
import json
import math
import random
import sys
from pathlib import Path
import bpy

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from coal_layout import grate_coals
sys.path.insert(0, str(here.parents[1] / 'VillageCarpenter/YardDetail'))
from geometry import SurfaceMesh, PALETTE

PALETTE.update(Iron=(.13,.13,.12), Leather=(.25,.12,.055), Stone=(.27,.25,.21),
               Brick=(.36,.18,.11), Coal=(.055,.05,.048), Ash=(.34,.32,.29))
out = here.parents[3] / 'SourceAssets/HillsVillageBlacksmith20261117/Workfloor'


def loft(m, rings, material, smooth=False, period=55):
    """Closed surfaces with continuous perimeter UVs and planar caps."""
    n = len(rings[0])
    starts = [m.vertices(r) for r in rings]
    heights = [0.]
    for a,b in zip(rings,rings[1:]):
        heights.append(heights[-1]+max(math.dist(p,q) for p,q in zip(a,b)))
    for i,(lower,upper) in enumerate(zip(rings,rings[1:])):
        distance = 0.
        for j,p in enumerate(lower):
            k=(j+1)%n
            end=distance+math.dist(p,lower[k])
            m.face([starts[i]+j,starts[i]+k,starts[i+1]+k,starts[i+1]+j],
                   [(distance/period,heights[i]/period),(end/period,heights[i]/period),
                    (end/period,heights[i+1]/period),(distance/period,heights[i+1]/period)],material,smooth)
            distance=end
    for i,indices in ((0,list(reversed(range(n)))),(-1,list(range(n)))):
        # Select the cap's projection plane for horizontal and longitudinal lofts.
        ranges=[max(p[t] for p in rings[i])-min(p[t] for p in rings[i]) for t in range(3)]
        a,b=sorted(sorted(range(3),key=lambda t:ranges[t],reverse=True)[:2])
        m.face([starts[i]+j for j in indices],[(rings[i][j][a]/period,rings[i][j][b]/period) for j in indices],material)


def block(m, center, size, mat, bevel=.45):
    x,y,z=center
    a,b,c=[v*.5 for v in size]
    s=min(bevel,a*.35,b*.35,c*.4)
    rings=[]
    for dz, inset in ((-c,s),(-c+s,0),(c-s,0),(c,s)):
        w,h=a-inset,b-inset
        shape=[(-w+s,-h),(w-s,-h),(w,-h+s),(w,h-s),(w-s,h),(-w+s,h),(-w,h-s),(-w,-h+s)]
        rings.append([(x+u,y+v,z+dz) for u,v in shape])
    loft(m,rings,mat)


def lump(m,seed,x,y,z,a,b,h,mat):
    rng=random.Random(seed)
    n=(8,6,5)[m.level]
    shape=[]
    for j in range(n):
        t=2*math.pi*(j+rng.uniform(-.16,.16))/n
        r=rng.uniform(.8,1.13)
        shape.append((a*math.cos(t)*r,b*math.sin(t)*r))
    rings=[[(x+u*scale+shift,y+v*scale,z+height*(.91+.13*rng.random())) for u,v in shape]
           for scale,shift,height in ((.75,0,0),(1.,0,h*.48),(.54,a*.10,h))]
    loft(m,rings,mat,period=22.)


def bellows(m):
    # Pierced timber stand and two continuous leather gussets between hardwood leaves.
    rng=random.Random(909)
    for x in (-31,24):
        for y in (-14,14):
            block(m,(x,y,21),(7,7,42),'Oak',.75)
        m.board(rng,(x,0,40),39,9,6,90,'Oak')
    for y in (-14,14):
        m.board(rng,(-3.5,y,12),61,5,6,0,'Oak')
    n=(36,24,14)[m.level]
    outline=[]
    for i in range(n):
        t=i*math.tau/n
        outline.append((-4+43*math.cos(t), math.sin(t)*(20.-10.4*math.cos(t))))
    def leaf(scale,z):
        return [(x*scale,y*scale,z+.085*x) for x,y in outline]
    loft(m,[leaf(.975,42),leaf(1,42.6),leaf(1,45.8),leaf(.985,46.4)],'Oak')
    folds=[(46,.95),(47.5,.99),(51,.90),(55,1.01),(58,.88),(62,1.0),(65,.94),(67,.97)]
    # The heel opens wider than the nose.
    def fold(shape, height):
        return [(x*shape,y*shape,46+.085*x+(height-46)*(.68-.009*x)) for x,y in outline]
    loft(m,[fold(scale,z) for z,scale in folds],'Leather',True,34)
    loft(m,[fold(.98,66),fold(1.015,67),fold(1.015,71),fold(.99,72)],'Oak')
    for h in (48,63):
        loft(m,[fold(1.005,h),fold(1.009,h+1.1)],'Leather',True,28)
    m.board(rng,(-48,0,58.5),29,6,3.6,0,'Oak',tilt=4)
    # Nozzle projects into the left cheek. Rings in the YZ plane face along X.
    nozzle=[]
    for x,r,z in [(29,8.5,53),(36,9,55),(39,7,56),(61,4.7,62),(64,5.3,63),(75,4,65)]:
        nozzle.append([(x,r*math.cos(i*math.tau/12),z+r*math.sin(i*math.tau/12)) for i in range(12)])
    loft(m,nozzle,'Iron',True,28)


def bunker(m):
    rng=random.Random(501)
    for x in (-32,32):
        for y in (-22,22):
            block(m,(x,y,24),(5.5,5.5,48),'Oak')
    for row in range(4):
        for y in (-22,22):
            if y<0 and row==3:continue
            m.board(rng,(0,y,6.5+10.4*row),69,3.7,10.1,0,'Oak')
        for x in (-32,32):
            m.board(rng,(x,0,6.5+10.4*row),42,3.8,10.1,90,'Oak')
    for x in (-25,25):
        block(m,(x,-24.1,16),(3.2,1.1,29),'Iron')
        if m.level==0:
            for z in (7,24):block(m,(x,-24.95,z),(1.5,.9,1.5),'Iron',.25)
    block(m,(0,0,21),(58,38,16),'Coal',2)
    for j in range(5):
        for i in range(7):
            k=7*j+i
            x=-24+8*i+rng.uniform(-1.1,1.1)
            y=-14+7*j+rng.uniform(-1.,1.)
            z=27+3*(1-(x/30)**2)+2*(1-(y/21)**2)
            lump(m,1110+k,x,y,z,rng.uniform(4.9,7),rng.uniform(4.5,6.),rng.uniform(5,9),'Coal')


def hearth(m):
    rng=random.Random(8102)
    # Small bed centred on the existing Niagara grate; the ledge below catches ash.
    for chunk in grate_coals(rng):
        lump(m,*chunk,'Coal')
    for i in range(9):
        x=-31+i*7+rng.uniform(-1.,1.)
        lump(m,700+i,x,-45+rng.uniform(-1.4,1.4),38.,4.4,3.4,rng.uniform(.6,2.3),'Ash')
    # Staggered facing returns at either side of the open firebox.
    for side in (-1,1):
        for row in range(5):
            x=57*side
            cuts=[-11.5,-3.8,11.5] if row%2 else [-11.5,3.1,11.5]
            for lo,hi in zip(cuts,cuts[1:]):
                block(m,(x+(lo+hi)/2,-50.2-rng.uniform(0,.35),24.7+row*13.4),
                      (hi-lo-.65,3.,12.6),'Brick',.7)
    for row in range(2):
        cuts=[-76,-47,-19,14,45,76] if row==0 else [-76,-59,-31,2,29,59,76]
        for lo,hi in zip(cuts,cuts[1:]):
            block(m,((lo+hi)/2,-56.1,4.7+8.25*row),(hi-lo-.95,3.1,7.65),'Stone',.72)
    # Rivet heads follow the slope of the sheet-metal hood instead of floating on a flat plane.
    for f in (.14,.53,.85):
        width=70-43*f
        y=-56+72*f
        z=168+78*f
        for x in (-width+5,0,width-5):
            lump(m,162+int(x+z),x,y-.7,z-.4,1.5,1.45,1.9,'Iron')


if __name__=='__main__':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    entries=[('Bellows',bellows,[((-2,0,32),(85,41,60))]),
             ('CoalBunker',bunker,[((0,0,20),(69,47,40))]),('HearthDressing',hearth,[])]
    rows=[]
    for order,(key,build,boxes) in enumerate(entries):
        name='SM_Smith'+key
        group=bpy.data.objects.new(name+'_LODs',None)
        group['fbx_type']='LodGroup'
        bpy.context.collection.objects.link(group)
        objs=[]
        triangles=[]
        for level in range(3):
            surface=SurfaceMesh(level)
            build(surface)
            obj=surface.object(name+'_LOD'+str(level))
            obj.parent=group
            obj.modifiers.new('Export triangulation','TRIANGULATE')
            triangles.append(sum(len(p.vertices)-2 for p in obj.data.polygons))
            objs.append(obj)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [group]+objs:obj.select_set(True)
        bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},
            axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,
            use_custom_props=True,add_leaf_bones=False)
        rows.append(dict(name=name,file=name+'.fbx',triangles=triangles,boxes=boxes))
        group.location.x=order*2.05
        for child in objs[1:]:
            child.hide_set(True)
            child.hide_render=True
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'SmithWorkfloor.blend'))
    (out/'models.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')

