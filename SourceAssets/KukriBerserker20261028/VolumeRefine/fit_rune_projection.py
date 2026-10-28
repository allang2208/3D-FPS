"""Fit an unwarped centimeter projection to each actual blade face."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
sources=json.loads((P.parent/'blade-layout-source.json').read_text('utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
glyph=bpy.data.images.load(str(P.parent/'Art/WolfSigil.png'));w,h=glyph.size
pixels=list(glyph.pixels);aspect=w/h;samples=[]
for y in range(0,h,max(1,h//88)):
    for x in range(0,w,max(1,w//64)):
        k=4*(y*w+x)
        if pixels[k+3]*max(pixels[k:k+3])>.24:samples.append(((x+.5)/w-.5,(y+.5)/h-.5))
results=[]
for source in sources:
    with bpy.data.libraries.load(source['blend'],link=False) as (a,b):b.objects=[source['object']]
    obj=b.objects[0];bpy.context.collection.objects.link(obj);m=obj.data
    bvh=BVHTree.FromPolygons([v.co for v in m.vertices],[list(p.vertices) for p in m.polygons])
    xmin,xmax=source['bounds'][0]
    def usable(x,z):
        for side in (-1,1):
            hit,n,face,d=bvh.ray_cast(Vector((x,.03*side,z)),Vector((0,-side,0)),.06)
            if hit is None or abs(n.y)<.965:return False
        return True
    def center(z):
        hits=[xmin+(xmax-xmin)*i/360 for i in range(361) if usable(xmin+(xmax-xmin)*i/360,z)]
        return (min(hits)+max(hits))/2 if hits else None
    best=None
    for z0 in (.15,.165,.18,.195,.21,.225):
        x0=center(z0);xa=center(z0-.010);xb=center(z0+.010)
        if None in (x0,xa,xb):continue
        angle=math.atan2(xb-xa,.02);c,s=math.cos(angle),math.sin(angle)
        def fits(height):
            for u,v in samples:
                x=x0+(u*c*aspect+v*s)*height;z=z0+(-u*s*aspect+v*c)*height
                if not all(usable(x+dx,z+dz) for dx,dz in ((0,0),(.0011,0),(-.0011,0),(0,.0011),(0,-.0011))):return False
            return True
        low,high=.016,.074
        if not fits(low):continue
        for _ in range(10):
            mid=(low+high)/2
            if fits(mid):low=mid
            else:high=mid
        height=low*.96
        # Prefer the broad central belly when its fit is effectively equal.
        score=height-abs(z0-.185)*.035
        if best is None or score>best['score']:
            best={'kind':source['kind'],'center_cm':[x0*100,z0*100],'angle_radians':angle,
                'width_cm':height*aspect*100,'height_cm':height*100,'source_aspect':aspect,'score':score}
    if not best:raise RuntimeError('No flat-face fit '+source['kind'])
    # Record the old UV allocation to distinguish resolution loss from physical aspect.
    m.calc_loop_triangles();uv=m.uv_layers.active.data;densities=[]
    old=json.loads((P.parent/'placements.json').read_text('utf-8'))
    prior=next(r for r in old if r['blade']==source['kind'])
    for t in m.loop_triangles:
        v=[m.vertices[i].co for i in t.vertices];p=sum(v,Vector())/3
        if abs(p.z-prior['center'][1])>.025 or abs(p.x-prior['center'][0])>.025 or abs(t.normal.y)<.88:continue
        a,b,c=[uv[k].uv for k in t.loops]
        area=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))*.5
        if t.area>1e-10:densities.append(math.sqrt(area/t.area)*2048/100)
    best['old_uv_pixels_per_cm_minmax']=[min(densities),max(densities)] if densities else []
    best['old_size_cm']=[prior['width_m']*100,prior['height_m']*100]
    results.append(best);print('RUNE_FIT '+json.dumps(best),flush=True)
(P/'projection-layouts.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
