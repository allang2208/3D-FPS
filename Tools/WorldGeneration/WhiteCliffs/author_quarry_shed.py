"""Rebuild the quarry stonemason's shelter at its original metre-scale footprint."""
import math
import random
import json
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ASSET = "SM_QuarryRuinedShed"
OUT = Path(__file__).resolve().parents[3] / "SourceAssets/HillsRiverLake20261117/Authored"
R = random.Random(69124)
verts, faces, slots, colours, texcoords = [], [], [], [], []
STONE, OAK = 0, 1


def point(p, colour, uv):
    verts.append(tuple(p))
    colours.append(colour)
    texcoords.append(uv)
    return len(verts) - 1


def face(indices, slot):
    faces.append(tuple(indices))
    slots.append(slot)


def strip(lower, upper, slot):
    for i in range(len(lower)):
        j = (i + 1) % len(lower)
        face((lower[i], lower[j], upper[j], upper[i]), slot)


def stone(pos, u0, u1, bottom, top, front, back, stain=0.25):
    # Irregular arrises on the faces of solid offcuts. Opposite edges bear on
    # their neighbours; the ends and front cheeks retain chips from splitting.
    width = u1 - u0
    h = ((top(u0) - bottom(u0)) + (top(u1) - bottom(u1))) / 2
    if width < .045 or h < .04:
        return
    cut = min(.17, width*.23, h*.48)
    low_l, low_r, up_l, up_r = [R.uniform(.17, 1.) * cut for _ in range(4)]
    outline = ((low_l,0), (width-low_r,0), (width,low_r/h), (width,1-up_r/h),
               (width-up_r,1), (up_l,1), (0,1-up_l/h), (0, low_l/h))
    chip = min(h*.18, width*.12, .052)
    shade = R.uniform(.02, .62)
    offset = (R.uniform(-8,8), R.uniform(-8,8))
    rings=[]
    for depth,inset in ((back,.79),(back+.035,1.),(front-chip,1.),(front,.87)):
        ring=[]
        for dx,t in outline:
            u = u0 + width/2 + (dx-width/2)*inset
            f = .5 + (t-.5)*inset
            z = bottom(u)+(top(u)-bottom(u))*f
            p = pos(u,depth + R.uniform(-.014,.014),z)
            wet = max(0.,1.0-max(z,0.)/.95)*.74
            lichen = min(.88,stain*(.38+.62*t)+wet*.24)
            ring.append(point(p,(wet,lichen,shade+.11*t,1),
                              (.47*u+offset[0],.47*z+offset[1])))
        if rings:
            strip(rings[-1],ring,STONE)
        rings.append(ring)
    face(reversed(rings[0]),STONE)
    # A biased centre creates several chipped planes across each outer face.
    u = (u0+u1)*.5+width*R.uniform(-.18,.18)
    z = bottom(u)+(top(u)-bottom(u))*R.uniform(.31,.68)
    center = point(pos(u,front+R.uniform(.005,.038),z),
                   (max(0.,1.-max(0.,z)/.95)*.74,stain*.68,shade,1),(.47*u+offset[0],.47*z+offset[1]))
    for i in range(len(outline)):
        face((rings[-1][i],rings[-1][(i+1)%len(outline)],center),STONE)


def wall(pos, first, last, crown, phase):
    bands=(-.12,.45,1.02,1.60,2.13,2.71,3.2)
    def bed(x,z):
        return z+.074*math.sin(x*1.08+phase+z*.7)+.036*math.cos(x*2.32+phase-z*.47)
    # A recessed rubble core closes open bedding joints and gives the broken
    # crown thickness. It ends beneath the top stones and clear of the doorway.
    n=math.ceil((last-first)/.26)
    previous=None
    for i in range(n+1):
        x=first+(last-first)*i/n
        roof=max(.02,crown(x)-.19)
        section=[]
        for d,z in ((-.18,-.15),(.13,-.15),(.13,roof),(-.18,roof)):
            section.append(point(pos(x,d,z),(.65,.46,.64,1),(.54*x,.54*z)))
        if previous: strip(previous,section,STONE)
        else: face(reversed(section),STONE)
        previous=section
    face(previous,STONE)
    for row,(base,cap) in enumerate(zip(bands,bands[1:])):
        x=first
        while x<last-.035:
            width=R.uniform(.64,1.16) if row!=0 else R.uniform(.73,1.34)
            end=min(last,x+width)
            if last-end<.21: end=last
            mid=(x+end)/2
            lower=lambda u:bed(u,base)+.005
            upper=lambda u:max(lower(u)+.021,min(bed(u,cap)-.004,crown(u)))
            if upper(mid)-lower(mid)>.092:
                joint=R.uniform(.39,.68)
                divide=lambda u:lower(u)+(upper(u)-lower(u))*joint+.042*math.sin(2.3*(u-mid))
                thick=R.uniform(.235,.347)
                weather=.06+.44*max(0.,math.sin(mid*.91+phase))*max(0.,1-base/2.7)
                if R.random()<.67 and upper(mid)-lower(mid)>.39:
                    stone(pos,x+.009,end-.006,lower,divide,thick,-.275,weather)
                    split=x+(end-x)*R.uniform(.36,.64)
                    for a,b in ((x,split),(split,end)):
                        stone(pos,a+.006,b-.005,divide,upper,thick+R.uniform(-.046,.037),-.272,weather)
                else:
                    stone(pos,x+.007,end-.006,lower,upper,thick,-.28,weather)
            x=end


def timber(a,b,w,d=None,chipped=False, board=False):
    """Eight-sided hewn section, with bark-edge wane, irregular ends and grain along the timber."""
    a,b=Vector(a),Vector(b)
    axis=(b-a).normalized()
    side=axis.cross(Vector((0,0,1)))
    if side.length<.015: side=Vector((1,0,0))
    side.normalize()
    normal=axis.cross(side).normalized()
    if normal.z<0:
        side=-side
        normal=-normal
    d=w if d is None else d
    if abs(axis.z)>.98:
        normal=axis.cross(side).normalized()
    line=b-a
    start=R.uniform(0.,4.)
    rings=[]
    corners=((-1,-.62),(-.77,-1),(.82,-1),(1,-.71),(1,.72),(.83,1),(-.86,1),(-1,.67))
    crook=R.uniform(-.043,.043) if board else R.uniform(-.017,.017)
    for row,t in enumerate((0.,.43,1.)):
        ring=[]
        for j,(u,v) in enumerate(corners):
            warp=R.uniform(-.10,.10) if row==2 and chipped else 0.
            p=a+t*line+(u*w*.5+math.sin(math.pi*t)*crook)*side+v*d*.5*normal
            p+=axis*warp+normal*R.uniform(-.055,.055)*d
            ring.append(point(p,(.01,0.,.12,1.),(start+t*line.length, .5*w*u+.5*d*v)))
        if rings: strip(rings[-1],ring,OAK)
        rings.append(ring)
    face(reversed(rings[0]),OAK)
    face(rings[-1],OAK)


def assemble():
    R.seed(69124)
    for data in (verts,faces,slots,colours,texcoords): data.clear()
    front=lambda u,d,z:(u,-3.-d,z)
    rear=lambda u,d,z:(u,2.96+d,z)
    left=lambda u,d,z:(-4.46-d,u,z)
    right=lambda u,d,z:(4.46+d,u,z)
    # An intact jamb on the windward side, a lower rubble return on the
    # loading side and a mostly closed back wall behind the bench.
    wall(front,-4.72,-1.38,lambda x:2.68+.14*math.sin(1.9*x),1.0)
    wall(front,1.37,4.72,lambda x:2.62-.48*(x-1.37)+.18*math.sin(x*1.9),2.6)
    wall(rear,-4.72,4.72,lambda x:2.88-.37*max(0.,x-1.1)+.1*math.sin(x*1.81),4.1)
    wall(left,-2.75,2.71,lambda y:2.69+.09*math.sin(y*1.5),.5)
    wall(right,-2.75,2.71,lambda y:1.12+.43*((y+2.75)/5.46)+.17*math.sin(y*1.55),2.2)
    # Add a few fallen offcuts against the collapsed return, inside its footprint.
    for x,y,w,h in ((3.83,-1.99,.67,.23),(3.55,-1.62,.50,.26),(3.79,-1.31,.41,.18),
                      (4.03,-1.71,.56,.20),(3.43,-1.85,.26,.15)):
        stone(lambda u,d,z:(x+u,y+d,z),-w/2,w/2,lambda u:-.06,lambda u:h-.10*u,.18,-.18,.5)
    # Door head and both cheeks take the front roof load. The opening is
    # wide enough to frame the stonecutting bench from outside.
    for x in (-1.32,1.32):
        timber((x,-3.,-.07),(x,-3.,2.65),.23,.26)
        timber((x,-2.96,2.07),(x*.64,-2.96,2.61),.13,.15)
    timber((-1.66,-3.,2.62),(1.66,-3.,2.62),.27,.27,True)
    def roof(x,y):return 4.05-abs(x)*.287-.045*(1.-(y/3.4)**2)
    for y in (-2.88,-.85,1.15,2.80):
        timber((-4.52,y,roof(-4.52,y)),(0,y,roof(0,y)),.20,.24,True)
        tip=4.54 if y<=-.85 else 2.34 if y<2. else 1.48
        timber((0,y,roof(0,y)),(tip,y,roof(tip,y)),.19,.23,True)
    timber((-4.36,-3.22,2.74),(-4.36,3.20,2.74),.20,.23,True)
    for y in (-2.75,-.84):
        timber((4.32,y,-.03),(4.32,y,roof(4.32,y)),.22)
    timber((4.32,-3.18,2.79),(4.32,-.63,2.79),.19,.22,True)
    timber((-1.34,-2.85,2.66),(0,-2.85,4.04),.19)
    timber((1.34,-2.85,2.66),(0,-2.85,4.04),.19)
    timber((0,2.77,.0),(0,2.77,4.05),.23)
    timber((0,2.77,3.01),(-1.5,2.77,3.63),.15)
    timber((0,-3.19,4.03),(0,3.20,4.03),.21,.22,True)
    # Purlins run along the roof, underneath each overlapping row of split shakes.
    for sign in (-1,1):
        for x in (.25,1.31,2.39,3.49,4.31):
            end=3.13 if sign<0 else (3.0 if x<1.5 else 1.12 if x<2.5 else -.85)
            timber((x*sign,-3.26,roof(x,-3.26)+.105),(x*sign,end,roof(x,end)+.105),.10,.11,True)
        for course in range(4):
            y=-3.33
            limit=3.31 if sign<0 else (2.98,1.34,-.54,-.98)[course]
            while y<limit-.04:
                w=min(R.uniform(.23,.38),limit-y)
                mid=y+w/2
                start=max(.02,course*1.12-.15)
                end=min(4.82,start+R.uniform(1.38,1.54))
                if sign<0 and course==3 and 1.54<mid<2.04: end-=.56
                if sign>0 and mid>limit-.55: end-=R.uniform(.20,.53)
                a=(sign*start,mid,roof(start,mid)+.19+.012*(3-course))
                b=(sign*end,mid+R.uniform(-.024,.024),roof(end,mid)+.23+.012*(3-course))
                timber(a,b,w+.012,R.uniform(.048,.069),True,True)
                y+=w
    # A solid slatted upper back below the surviving roof keeps the workshop
    # shaded. The worked blank and trestles sit to one side of the entry.
    for i in range(15):
        x=-3.68+i*.297
        timber((x,2.73,2.73),(x,2.73,roof(x,2.73)-.09),.278,.052,True)
    for y in (.23,1.18):
        for x in (-1.06,.77):
            timber((x-.08,y+.06,-.04),(x,y,.83),.12)
    for i in range(4):
        y=.22+i*.28
        timber((-1.35,y,.86),(1.04,y,.86),.28,.10,True,True)
    stone(lambda u,d,z:(u,.68+d,z),-.75,.22,lambda u:.915,lambda u:1.12+.015*u,.27,-.24)
    # Reclaimed split planks are stacked at the intact back corner.
    for i in range(4):
        timber((-4.09,1.0+i*.13,.12+i*.025),(-2.26,1.04+i*.13,.14+i*.025),.14,.10,True)
    mesh=bpy.data.meshes.new(ASSET)
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    for key in ("Stone","Oak"):
        mesh.materials.append(bpy.data.materials.get(key) or bpy.data.materials.new(key))
    colour=mesh.color_attributes.new(name="RockWeather",type="BYTE_COLOR",domain="POINT")
    for data,val in zip(colour.data,colours): data.color=val
    uv=mesh.uv_layers.new(name="SurfaceMetres")
    for p,slot in zip(mesh.polygons,slots):
        p.material_index=slot
        indices=[mesh.loops[loop].vertex_index for loop in p.loop_indices]
        coords=[texcoords[idx] for idx in indices]
        area=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(coords,coords[1:]+coords[:1]))
        if abs(area)<1.e-6 or (slot==STONE and abs(p.normal.z)>.7):
            axes=((1,2),(0,2),(0,1))[max(range(3),key=lambda k:abs(p.normal[k]))]
            coords=[tuple(.47*verts[idx][axis] for axis in axes) for idx in indices]
        for loop,mapped in zip(p.loop_indices,coords):
            uv.data[loop].uv=mapped
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj=bpy.data.objects.new(ASSET,mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ASSET+".fbx")),use_selection=True,object_types={"MESH"},
                             axis_forward="-Y",axis_up="Z",mesh_smooth_type="FACE",use_tspace=True,
                             bake_anim=False,add_leaf_bones=False)
    return obj

if __name__ == "__main__":
    kit=OUT/"QuarryKit.blend"
    if kit.is_file():
        bpy.ops.wm.open_mainfile(filepath=str(kit))
        previous=bpy.data.objects.get(ASSET)
        if previous is None:
            raise RuntimeError("Missing original quarry shed in "+str(kit))
        transform=previous.matrix_world.copy()
        bpy.data.objects.remove(previous,do_unlink=True)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    shed=assemble()
    if kit.is_file():
        shed.matrix_world=transform
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(kit))
    manifest=OUT/"manifest.json"
    if manifest.is_file():
        rows=json.loads(manifest.read_text(encoding="utf8"))
        for row in rows:
            if row["name"]==ASSET:
                row.update(slots=[m.name for m in shed.data.materials],vertices=len(shed.data.vertices))
        manifest.write_text(json.dumps(rows,indent=2),encoding="utf8")
    print("QUARRY_SHED_FBX_SAVED",len(shed.data.vertices),len(shed.data.polygons))
