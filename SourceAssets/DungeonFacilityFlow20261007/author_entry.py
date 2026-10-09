"""Side-entry variant only. Reuse the approved fractured concrete algorithm.
No subject map, original hall mesh, rendering or gameplay execution is changed.
"""
import bpy, bmesh, sys, json, math, hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent; PROJECT=ROOT.parents[1]
OPEN_REAR='--open-rear' in sys.argv
OUT=ROOT/'Authored'; OUT.mkdir(exist_ok=True)
BASE='/Game/Dungeons/FacilityFlow20261007'
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'))
import geometry as g
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonRoomShells20260922/Scripts'))
import room_detail_geometry as damage
ROLES=json.loads((PROJECT/'SourceAssets/DungeonReceptionHall20261006/Config/materials.json').read_text('utf8'))
ROLES['FractureConcrete']=dict(ROLES['Concrete'])
ROLES['ServicePaint']=dict(ROLES['Steel']); ROLES['ServiceHardware']=dict(ROLES['Steel'])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'; bpy.context.scene.unit_settings.scale_length=1
g.ROOM='Entry'; materials={}
for role,r in ROLES.items():
    m=bpy.data.materials.new('FF_'+role);m.diffuse_color=(*r['basecolor_linear'],1);materials[role]=m

# Replace whole merged outer-wall and trim parts, so no hidden intact face
# remains behind the opening. All unmodified dimensions match the source hall.
for side in (-1,1):
    if side==1:g.box('OuterWalls',(0,16.66,5),(48.6,.32,10),'Concrete',collision=True)
    for x,width in [(-24,4),(24,3)]:
        span=16.5-width/2
        g.box('OuterWalls',(x,side*(width/2+span/2),5),(.36,span,10),'Concrete',collision=True)
    for z in (.10,1.18,4.65,5.65):
        ranges=[(-23.85,23.85)] if side==1 or z>4 else [(-23.85,-21.25),(-16.35,23.85)]
        for lo,hi in ranges:g.box('WallTrim',((lo+hi)/2,side*16.48,z),(hi-lo,.038,.09 if z in (.1,4.65) else .032),'Teal')
for x,width,height in [(-24,4,3.4),(24,3,3)]:
    g.box('OuterWalls',(x,0,(height+10)/2),(.36,width,10-height),'Concrete',collision=True)
# Intact closed front vestibule. It remains a facade, not a graph connection.
g.box('FrontClosure',(-27.12,0,1.7),(.24,4.24,3.4),'Concrete',collision=True)
for y in (-1.01,1.01):
    g.box('FrontClosure',(-27.252,y,1.52),(.025,1.99,3.02),'Teal')
    for yy in (y-.94,y+.94):g.box('FrontClosure',(-27.277,yy,1.52),(.025,.035,3.01),'Steel')
g.box('FrontClosure',(-27.285,0,1.08),(.05,3.95,.12),'Steel')

# Existing layered chipped edge / aggregate / bent rebar recipe.
# Triangulated face prisms give closed convex collision only in solid concrete.
seen=set()
def poly(kind,vs,fs,mat,uv=None,smooth=False):
    mapped='OuterWalls' if kind=='Shell' else 'PassageDetails' if kind=='Debris' else 'BreachRebar'
    g.poly(mapped,vs,fs,mat,uv,smooth)
    if kind=='Shell' and mat=='Concrete':
        for f in fs:
            if len(f)!=3:continue
            tri=[(vs[i][0],vs[i][2]) for i in f];key=tuple(sorted((round(x,5),round(z,5)) for x,z in tri))
            if key in seen:continue
            seen.add(key)
            points=[(x,-16.66+y,z) for y in (-.16,.16) for x,z in tri]
            g.hull('OuterWalls',points,[(2,1,0),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)])
def prism(kind,outline,start,direction,normal,depth,mat):
    vs=[tuple(Vector((start.x,start.y,0))+Vector((direction.x,direction.y,0))*t+Vector((normal.x,normal.y,0))*d+Vector((0,0,z))) for d in (-depth/2,depth/2) for t,z in outline]
    n=len(outline);fs=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    g.poly('OuterWalls',vs,fs,mat);g.hull('OuterWalls',vs,fs)
damage.setup(dict(CFG=dict(style=dict(wall_thickness=.32)),poly=poly,box=g.box,prism=prism))
damage.breach_wall(Vector((-24.3,-16.66,0)),Vector((1,0,0)),Vector((0,1,0)),48.6,10,
    dict(left=3.15,right=7.85,height=3.55),'Concrete')

g.box('BreachThreshold',(-18.8,-16.65,-.003),(3.2,.70,.018),'Steel',collision=True)

# Twelve-metre service passage, regular 3 m / 2.8 m at its rear, opening out
# before the broken wall. Flared end reveals the fracture rather than hiding it.
# Blender +Y is forward; after import UE -Y is forward.
g.box('Passage',(0,4.5,-.16),(3.6,9,.32),'Concrete',collision=True)
g.box('Passage',(0,10.5,-.16),(5.22,3,.32),'Concrete',collision=True)
for side in (-1,1):
    g.box('Passage',(side*1.66,4.5,1.56),(.32,9,3.12),'Concrete',collision=True)
    outline=[(side*1.50,9),(side*2.45,12),(side*2.77,12),(side*1.82,9)]
    g.prism('Passage',outline,0,4.16,'Concrete',collision=True)
    g.rounded_pipe('PassageDetails',[(side*1.45,.25,2.25),(side*1.45,8.8,2.25),(side*2.38,11.85,2.25)],.045,'Steel',16)
    for y in (1.5,4.5,7.5):g.bolt('PassageDetails',(side*1.492,y,2.24),(-side,0,0),.02)
g.box('Passage',(0,4.5,2.96),(3.64,9,.32),'Concrete',collision=True)
g.box('Passage',(0,10.5,4.02),(5.54,3,.28),'Concrete',collision=True)
# Vertical change of ceiling is closed above head height, never a floor step.
g.box('Passage',(0,9.05,3.51),(3.64,.10,1.10),'Concrete',collision=True)
if not OPEN_REAR:
    g.box('Passage',(0,-.10,1.56),(3.64,.20,3.12),'Concrete',collision=True)
for y in (2.0,6.0):
    g.box('PassageDetails',(0,y,2.70),(.86,.20,.14),'Teal')
    g.box('PassageDiffusers',(0,y,2.62),(.78,.16,.025),'Glow')
# Debris stays against the flared jambs; no raised rubble across the walk line.
import random
r=random.Random(10727)
for side in (-1,1):
    for i in range(16):
        damage.chunk((side*r.uniform(1.78,2.28),r.uniform(10.8,11.95),r.uniform(.025,.06)),(.16,.19,.085),r,'FractureConcrete','Debris')

records=[]
for (_,kind),data in g.G.items():
    if OPEN_REAR and kind!='Passage':continue
    name='SM_FacilityFlow_'+kind+('OpenRear' if OPEN_REAR else ''); mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    order=list(dict.fromkeys(data['m']))
    for role in order:mesh.materials.append(materials[role])
    uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for face,role,coords,smooth in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
        face.material_index=order.index(role);face.use_smooth=smooth
        axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
        scale=ROLES[role].get('uv_meters_override',ROLES[role].get('uv_meters',1))
        for j,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=coords[j] if coords else (p[axes[0]]/scale,p[axes[1]]/scale)
            age.data[li].color=(.12+.15*math.exp(-max(0,p.z)/.3),0,0,1)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    mod=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    cols=[]
    for i,(vs,fs) in enumerate(g.C.get((g.ROOM,kind),[])):
        cm=bpy.data.meshes.new('UCX_'+name+'_%03d'%i);cm.from_pydata(vs,[],fs);cm.update();co=bpy.data.objects.new(cm.name,cm);bpy.context.collection.objects.link(co);co.select_set(True);cols.append(co)
    fbx=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    for co in cols:co.hide_set(True);co.hide_render=True
    records.append(dict(name=name,kind=kind,mesh=BASE+'/Meshes/'+name,fbx=str(fbx),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),materials={'FF_'+r:ROLES[r]['existing_ue_path'] for r in order},collision=bool(cols),nanite=kind!='PassageDiffusers',cast_shadow=True))
    print('FACILITY_ENTRY_EXPORTED',kind,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('FacilitySideEntryOpenRear.blend' if OPEN_REAR else 'FacilitySideEntry.blend')))
(ROOT/('geometry-open-rear.json' if OPEN_REAR else 'geometry.json')).write_text(json.dumps(dict(meshes=records),indent=2),encoding='utf8')
