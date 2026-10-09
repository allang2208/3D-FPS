"""Reuse the accepted server rack, separate its upper-left cartridge, add a real bay."""
import bpy,bmesh,json,sys,math,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT.parent;PROJECT=ROOT.parents[2]
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE='/Game/Dungeons/PowerTheme20261004/ServerContainers20261006'
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonDataArchive20260930/Equipment20260930/Scripts'))
import mesh_helpers as g
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
source=SOURCE/'TextCards20261005/Authored/SM_Archive_ServerRack_V1.fbx'
bpy.ops.import_scene.fbx(filepath=str(source))
original=bpy.data.objects['SM_Archive_ServerRack_V1'];mesh=original.data
points=[original.matrix_world@v.co for v in mesh.vertices]
normals=[original.matrix_world.to_3x3()@n.vector for n in mesh.corner_normals]
source_mats=list(mesh.materials)
MATERIALS={source_mats[0].name:'/Game/Dungeons/PowerTheme20261004/RefineV2/Materials/M_Power_ServerChinese',
    source_mats[1].name:'/Game/Dungeons/PowerTheme20261004/TextCards20261005/Materials/M_Power_TextCards'}
# The original chassis and fascia are closed connected solids. Replace just
# these two solids with folded members around a genuine cartridge aperture.
parent=list(range(len(points)))
def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
for f in mesh.polygons:
    first=find(f.vertices[0])
    for v in f.vertices[1:]:parent[find(v)]=first
components={}
for f in mesh.polygons:components.setdefault(find(f.vertices[0]),[]).append(f.index)
housing=set()
targets=[((0,-.19,1.58),(.588,.61,.431)),((-.081,-.527,1.58),(.416,.018,.427))]
for faces in components.values():
    ids={v for i in faces for v in mesh.polygons[i].vertices}
    lo=[min(points[v][k] for v in ids) for k in range(3)]
    hi=[max(points[v][k] for v in ids) for k in range(3)]
    for center,size in targets:
        if all(abs((lo[k]+hi[k])/2-center[k])<.00005 and abs(hi[k]-lo[k]-size[k])<.00005 for k in range(3)):
            housing.update(faces)
def in_blade(p):return -.2616<=p.x<=-.1564 and -.632<=p.y<=-.5244 and 1.4039<=p.z<=1.7561
blade={f.index for f in mesh.polygons if all(in_blade(points[v]) for v in f.vertices)}
if not housing or not blade:raise RuntimeError('The accepted server source does not contain the expected cartridge/chassis geometry')

def subset(name,indices):
    verts=[];faces=[];coords=[];mats=[];smooth=[];ns=[]
    for i in indices:
        f=mesh.polygons[i];start=len(verts)
        verts.extend(tuple(points[v]) for v in f.vertices);faces.append(tuple(range(start,start+len(f.vertices))))
        mats.append(f.material_index);smooth.append(f.use_smooth)
        for li in f.loop_indices:coords.append(tuple(mesh.uv_layers[0].data[li].uv));ns.append(tuple(normals[li]))
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update()
    for mat in source_mats:m.materials.append(mat)
    uv=m.uv_layers.new(name='UVMap')
    for i,co in enumerate(coords):uv.data[i].uv=co
    for f,slot,sm in zip(m.polygons,mats,smooth):f.material_index=slot;f.use_smooth=sm
    m.normals_split_custom_set(ns);m.update()
    o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o);return o
body=subset('SM_Power_ServerContainer_Body',[f.index for f in mesh.polygons if f.index not in blade|housing])
drawer=subset('SM_Power_ServerContainer_Cartridge',sorted(blade))
for o in list(bpy.context.scene.objects):
    if o not in (body,drawer):bpy.data.objects.remove(o,do_unlink=True)

def begin():
    for values in (g.V,g.F,g.UV,g.SMOOTH):values.clear()
def box_between(lo,hi,mat,bevel=.0008):
    g.box(tuple((lo[i]+hi[i])/2 for i in range(3)),tuple(hi[i]-lo[i] for i in range(3)),mat,bevel)
def add_to(obj):
    m=bpy.data.meshes.new(obj.name+'_NewInterior');m.from_pydata(g.V,[],g.F);m.materials.append(source_mats[0]);m.update()
    uv=m.uv_layers.new(name='UVMap')
    for f,coords,sm in zip(m.polygons,g.UV,g.SMOOTH):
        f.use_smooth=sm
        for li,co in zip(f.loop_indices,coords):uv.data[li].uv=co
    o=bpy.data.objects.new(m.name,m);bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Manufactured interior normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()

begin();x=-.209;z=1.58
# Split the original module enclosure, including its front fascia. Nothing
# remains across the aperture once the upper-left cartridge is pulled out.
for low,high in [((-.294,-.495,1.3645),(-.260,.115,1.7955)),
                 ((-.158,-.495,1.3645),(.294,.115,1.7955)),
                 ((-.260,-.495,1.3645),(-.158,.115,1.409)),
                 ((-.260,-.495,1.751),(-.158,.115,1.7955)),
                 ((-.260,.091,1.409),(-.158,.115,1.751))]:box_between(low,high,'graphite')
for low,high in [((-.289,-.536,1.3665),(-.260,-.518,1.7935)),
                 ((-.158,-.536,1.3665),(.127,-.518,1.7935)),
                 ((-.260,-.536,1.3665),(-.158,-.518,1.409)),
                 ((-.260,-.536,1.751),(-.158,-.518,1.7935))]:box_between(low,high,'ivory')
# Fixed slide channels, rear connector and socket contact blocks.
for dx in (-.047,.047):
    for zz in (z-.133,z+.133):g.box((x+dx,-.215,zz),(.006,.598,.012),'steel',.0005)
g.box((x,.080,z),(.067,.014,.184),'rubber',.001)
for i in range(9):g.box((x-.023+i*.0058,.071,z),(.0028,.004,.165),'steel',.0003)
add_to(body)

begin()
# 59 cm deep cartridge; the original handle, indicator and face remain intact.
g.box((x,-.228,z-.160),(.082,.589,.004),'steel',.0006)
g.box((x,-.228,z+.160),(.082,.589,.004),'steel',.0006)
g.box((x,.064,z),(.082,.004,.316),'steel',.0006)
for dx in (-.0405,.0405):
    for zz,hh in ((z-.090,.136),(z+.09,.136)):
        g.box((x+dx,-.228,zz),(.003,.588,hh),'steel',.0005)
    # A real narrow ventilation band between the folded side panels.
    for i in range(36):g.box((x+dx,-.511+i*.016, z),(.003,.006,.046),'steel',.0004)
    for zz in (z-.132,z+.132):g.box((x+dx,-.226,zz),(.006,.555,.008),'graphite',.0005)
# Interior board and finned components visible through the side vents.
g.box((x+.024,-.228,z),(.002,.530,.284),'green',.0005)
for yy in (-.39,-.21,-.035):
    g.box((x+.014,yy,z),(.015,.105,.076),'rubber',.001)
    for i in range(7):g.box((x-.003,yy-.044+i*.014,z),(.021,.004,.080),'steel',.0005)
for yy in (-.455,-.30,-.14,.018):
    for zz in (z-.112,z+.112):g.lathe((x-.0428,yy,zz),(-1,0,0),[(0,.004),(.001,.004)],'steel',12)
g.box((x,.068,z),(.061,.008,.176),'rubber',.0007)
add_to(drawer)

records=[]
def export(obj,boxes):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
    # Use the cartridge mount as its own pivot; the native drawer hinge supplies
    # this offset and translates the complete part 32 cm toward the operator.
    pivot=Vector((x,-.5245,z)) if obj==drawer else Vector((0,0,0))
    for v in obj.data.vertices:v.co-=pivot
    collisions=[]
    for i,(center,size) in enumerate(boxes):
        bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(center)-pivot);c=bpy.context.object;c.name='UCX_'+obj.name+'_%02d'%i;c.dimensions=size
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);collisions.append(c)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    for c in collisions:c.select_set(True)
    bpy.context.view_layer.objects.active=obj;fbx=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,
        mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    for c in collisions:bpy.data.objects.remove(c,do_unlink=True)
    obj.location=pivot
    records.append(dict(name=obj.name,mesh=BASE+'/Meshes/'+obj.name,fbx=str(fbx),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),
        materials={m.name:MATERIALS[m.name] for m in obj.data.materials},nanite=obj==body,collision_hulls=len(boxes),triangles=len(obj.data.polygons),pivot_blender_m=list(pivot)))
    print('POWER_SERVER_CONTAINER_AUTHORED',obj.name,len(obj.data.polygons),flush=True)
export(body,[((0,0,1.075),(.74,1.10,2.15))])
export(drawer,[((x,-.276,z),(.106,.690,.352))])
bpy.context.scene['tests_run']=False;bpy.context.scene['rendered']=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ServerPulloutContainer.blend'))
(ROOT/'manifest.json').write_text(json.dumps(dict(base=BASE,source_fbx=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    meshes=records,hinge_ue_cm=[x*100,52.45,z*100],travel_ue_cm=[0,32,0],opening_seconds=.55,tests_run=False,rendered=False),indent=2),encoding='utf8')
