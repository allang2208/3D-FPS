"""Arrival trim, two fitted lights and a wall-connected ventilation branch."""
from pathlib import Path
import bpy,bmesh,sys,json,hashlib,math
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonFacilityTransit20261007/Scripts'))
import geometry as g
sys.path.insert(0,str(PROJECT/'SourceAssets/ReceptionFinish20261010'))
from concrete_mesh import project_uv
sys.path.insert(0,str(ROOT))
from frame_mesh import prepare_frame,localize_uv
BASE='/Game/Dungeons/TransitFinish20261010'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
g.ROOM='TransitFinish'
materials=dict(Teal='/Game/Dungeons/ReceptionHall20261006/Materials/M_Reception_Teal',
    Steel='/Game/Dungeons/SeamMetal20260923/Materials/MI_BareSteel',
    Dark='/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_KettleRubber_V6',
    Glow='/Game/Dungeons/HallLighting20261007/Materials/M_SteadyDiffuser')

# West opening remains 300 x 300 cm. The steel lining folds through the actual
# 32 cm wall depth and meets the arrival corridor; it never fills the doorway.
for side in (-1,1):
    g.box('ArrivalFrame',(-23.98,side*1.58,1.5),(.06,.16,3),'Teal')
    g.box('ArrivalFrame',(-24.135,side*1.511,1.5),(.37,.022,3),'Steel')
    g.box('ArrivalFrame',(-23.936,side*1.58,.26),(.02,.15,.50),'Steel')
    for z in (.22,1.50,2.78):g.bolt('ArrivalFrame',(-23.941,side*1.60,z),(1,0,0),.009)
g.box('ArrivalFrame',(-23.98,0,3.08),(.06,3.32,.16),'Teal')
g.box('ArrivalFrame',(-24.135,0,3.011),(.37,3,.022),'Steel')
g.box('ArrivalFrame',(-24.02,0,.006),(.54,2.98,.012),'Steel')

# Match the existing lower-gallery diffuser plane (368.9 cm) and row X=-20m.
# The separate arrival fitting runs across the doorway, on the same soffit.
for x,y,turned in ((-20,0,False),(-23,0,True)):
    w,d=(.30,1.30) if turned else (1.30,.30)
    g.box('FixtureHousings',(x,y,3.765),(w,d,.11),'Teal')
    g.box('FixtureHousings',(x,y,3.711),(w-.025,d-.025,.028),'Steel')
    g.box('FixtureDiffusers',(x,y,3.70),(.24 if turned else 1.22,1.22 if turned else .24,.022),'Glow')
    for offset in (-.43,.43):
        px,py=(x,y+offset) if turned else (x+offset,y)
        g.box('FixtureHousings',(px,py,3.82),(.10,.10,.01),'Dark')

# Move the existing 1.84m vent away from the theme-facade shoulder. Its rear rim
# meets the wall at Y=18m. Connect above it below the high service pipe (Z=7.3m).
cx,cy=14.5,17.08
def ring(y,z,half_x,half_d,angle=0):
    return [(cx+sx*half_x,y+sy*half_d*math.cos(angle),z-sy*half_d*math.sin(angle))
        for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1))]
def sleeve(rings):
    vertices=[v for r in rings for v in r];faces=[]
    for j in range(len(rings)-1):
        for i in range(4):faces.append((j*4+i,j*4+(i+1)%4,(j+1)*4+(i+1)%4,(j+1)*4+i))
    g.poly('VentConnection',vertices,faces,'Teal')
sleeve([ring(cy,5.37,.895,.895),ring(cy,6.04,.40,.325)])
arc=[ring(cy+.60*(1-math.cos(t)),6.04+.60*math.sin(t),.40,.325,t)
    for t in [math.pi*.5*i/12 for i in range(13)]]
arc.append(ring(18.04,6.64,.40,.325,math.pi/2));sleeve(arc)
# Throat flange, folded wall collar, fastening rails and side brackets.
for side in (-1,1):
    g.box('VentMounts',(cx+side*.42,cy,6.04),(.04,.73,.055),'Steel')
    g.box('VentMounts',(cx,cy+side*.345,6.04),(.80,.04,.055),'Steel')
    g.box('VentMounts',(cx+side*.445,17.99,6.64),(.09,.06,.83),'Steel')
    g.box('VentMounts',(cx,17.99,6.64+side*.37),(.80,.06,.09),'Steel')
    g.box('VentMounts',(cx+side*.97,17.97,4.49),(.10,.07,1.84),'Teal')
    for z in (3.66,4.49,5.32):g.bolt('VentMounts',(cx+side*.97,17.928,z),(0,-1,0),.012)
    for z in (3.88,5.10):g.box('VentMounts',(cx+side*.925,17.50,z),(.09,.98,.06),'Steel')
    for z in (6.30,6.98):g.bolt('VentMounts',(cx+side*.445,17.949,z),(0,-1,0),.010)

records=[]
for (_,kind),data in g.G.items():
    mesh=bpy.data.meshes.new(kind);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
    roles=list(dict.fromkeys(data['m']))
    for role in roles:mesh.materials.append(bpy.data.materials.get('TF_'+role) or bpy.data.materials.new('TF_'+role))
    for face,role in zip(mesh.polygons,data['m']):face.material_index=roles.index(role)
    obj=bpy.data.objects.new('SM_TransitFinish_'+kind+('V2' if kind=='ArrivalFrame' else ''),mesh);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    if kind not in ('FixtureDiffusers','VentConnection'):
        bevel=obj.modifiers.new('Small fabricated edge','BEVEL');bevel.width=.0015;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(40)
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    tri=obj.modifiers.new('Triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    obj.data.update()
    if kind=='ArrivalFrame':prepare_frame(obj.data)
    project_uv(obj.data)
    if kind=='ArrivalFrame':localize_uv(obj.data)
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    records.append(dict(name=obj.name,kind=kind,mesh=BASE+'/Meshes/'+obj.name,fbx=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        materials={'TF_'+r:materials[r] for r in roles},collision=False,cast_shadow=kind!='FixtureDiffusers',nanite=kind!='FixtureDiffusers',triangles=len(obj.data.polygons)))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TransitFinish.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records),indent=2),encoding='utf8')
print('TRANSIT_FINISH_AUTHORED',len(records))
