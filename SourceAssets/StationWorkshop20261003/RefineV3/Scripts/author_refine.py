"""Three scoped source edits; preserve accepted meshes, UVs and material slots."""
import json, math, re, sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;PROJECT=PARENT.parents[1]
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE='/Game/Dungeons/StationWorkshop20261003/RefineV3'
sys.path.insert(0,str(PARENT/'Scripts'))
import geometry as g
g.OUT=OUT;g.BASE=BASE;g.MAP['Concrete']=BASE+'/Materials/M_Workshop_FlatConcrete'
g.MAP.update(PaintedSteel='/Game/Dungeons/SeamMetal20260923/Materials/MI_PaintedSteel',
    BareSteel='/Game/Dungeons/SeamMetal20260923/Materials/MI_BareSteel')
for key in ('PaintedSteel','BareSteel'):g.MATS[key]=bpy.data.materials.new('RS_'+key)
read=lambda p:json.loads(p.read_text('utf-8-sig'))
records=[]

def load_object(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.objects=[name]
    ob=dst.objects[0]
    if not ob:raise RuntimeError('Author source unavailable: '+name)
    bpy.context.scene.collection.objects.link(ob);ob.hide_set(False);ob.hide_render=False
    return ob

def export(ob,name,materials,collision=False):
    ob.name=name;ob.location=(0,0,0);g.select(ob)
    file=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    records.append(dict(name=name,fbx=str(file),asset=BASE+'/Meshes/'+name,materials=materials,
        triangles=sum(len(p.vertices)-2 for p in ob.data.polygons),nanite=True,collision=collision,
        complex_collision=collision))
    ob.hide_set(True)

# A single slab: bottom at 320 cm, thickness extends upward. No displacement or noisy normal.
# UE positive room Y maps to Blender negative Y. Fit the wall's 14 cm outer thickness.
g.box((5,-3.5,3.28),(10.14,7.14,.16),'Concrete',0)
roof=g.emit('SM_SW_Roof',hulls=[((5,-3.5,3.28),(10.14,7.14,.16))]);records.extend(g.records);g.records.clear()

# The tray and ratchet are islands within the accepted combined workbench component.
# Select the ratchet's original construction vertices, rather than a bounding rectangle
# that would also capture the tray lip or its loose washers.
kit=PROJECT/'SourceAssets/DungeonWorkbenchKit20260921'
entry=next(e for e in read(kit/'Authored/manifest.json')['components'] if e['id']=='Fab_BenchRetained')
bench=load_object(kit/'Authored/DungeonWorkbenchKit.blend',entry['name'])
bench.location=(0,0,0)
surface=PROJECT/'SourceAssets/DungeonWorkshopSurface20260921/Authored/DungeonWorkshopSurfaceDetails.blend'
with bpy.data.libraries.load(str(surface),link=False) as (src,dst):
    dst.collections=[n for n in src.collections if n.startswith('SOURCE_BenchDetail')]
collections=dst.collections
for collection in collections:
    bpy.context.scene.collection.children.link(collection);collection.hide_viewport=False
prefixes=('Forged oval ratchet body','Ergonomic ratchet grip','Quick release button','Head cover seam','Reversing selector')
points=[]
deps=bpy.context.evaluated_depsgraph_get()
for ob in [o for c in collections for o in c.all_objects]:
    if not ob.name.startswith(prefixes):continue
    mesh=bpy.data.meshes.new_from_object(ob.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
    for v in mesh.vertices:
        p=ob.matrix_world@v.co
        points.append(Vector((-p.x,1.48-p.y,p.z-.939)))
    bpy.data.meshes.remove(mesh)
if not points:raise RuntimeError('Ratchet source construction unavailable')
tree=KDTree(len(points))
for i,p in enumerate(points):tree.insert(p,i)
tree.balance();moved=0
for v in bench.data.vertices:
    _,_,distance=tree.find(v.co)
    if distance<.00002:v.co.x-=.14;moved+=1
if not moved:raise RuntimeError('Ratchet could not be selected from the accepted assembly')
bench.data.update()
for collection in collections:collection.hide_viewport=True;collection.hide_render=True
materials={re.sub(r'[._][0-9]{3}$','',m.name):entry['material_paths'][re.sub(r'[._][0-9]{3}$','',m.name)] for m in bench.data.materials}
export(bench,'SM_SW_BenchRetained',materials)

# Keep the accepted upper bridge and its stair rails byte-for-byte in geometry/UV.
# Only the two recovery stair rails and the west flat guards have negative X.
station=PROJECT/'SourceAssets/DungeonTransitStation20260928'
old=load_object(station/'Authored/AbandonedTransitStation_Subject.blend','SM_Station_Railings')
src=old.data;faces=[f for f in src.polygons if not all(src.vertices[i].co.x<0 for i in f.vertices)]
used=sorted({i for f in faces for i in f.vertices});idx={i:j for j,i in enumerate(used)}
loops=[li for f in faces for li in f.loop_indices]
normals=[src.corner_normals[i].vector.copy() for i in loops]
mesh=bpy.data.meshes.new('Accepted upper railings')
mesh.from_pydata([src.vertices[i].co[:] for i in used],[],[[idx[i] for i in f.vertices] for f in faces]);mesh.update()
for mat in src.materials:mesh.materials.append(mat)
for a,b in zip(faces,mesh.polygons):b.material_index=a.material_index;b.use_smooth=a.use_smooth
for layer in src.uv_layers:
    target=mesh.uv_layers.new(name=layer.name)
    for j,i in enumerate(loops):target.data[j].uv=layer.data[i].uv
for layer in src.color_attributes:
    target=mesh.color_attributes.new(name=layer.name,type=layer.data_type,domain=layer.domain)
    for j,i in enumerate(loops if layer.domain=='CORNER' else used):target.data[j].color=layer.data[i].color
mesh.normals_split_custom_set(normals);old.data=mesh
cfg=read(station/'Config/room.json')['track'];x0=cfg['x'][0];floor=cfg['floor']
steps=cfg['recovery_steps'];going=cfg['recovery_going'];width=cfg['recovery_width'];end=x0+steps*going
height=1.1;middle=.52;post_bases=[]

def post(x,y,z,top):
    g.box((x,y,z+.009),(.115,.115,.018),'BareSteel',.002)
    g.tube([(x,y,z+.018),(x,y,top)],.03,'PaintedSteel')
    for dx in (-.036,.036):
        g.cylinder((x+dx,y,z+.02),.006,.005,'BareSteel',sides=12)
    post_bases.append([x,y,z])

def flat_guard(y0,y1):
    x=x0-.08
    for z in (middle,height):g.tube([(x,y0,z),(x,y1,z)],.026,'PaintedSteel')
    count=max(1,math.ceil(abs(y1-y0)/1.25))
    for i in range(count+1):post(x,y0+(y1-y0)*i/count,0,height)

axis=width/2-.12
flat_guard(cfg['y'][0],-axis);flat_guard(axis,cfg['y'][1])
for y in (-axis,axis):
    for h in (middle,height):
        g.tube([(x0-.08,y,h),(x0+going*.5,y,floor/steps+h),
            (end-going*.5,y,floor+h),(end+.20,y,floor+h)],.026,'PaintedSteel')
    for i in (0,3,6,9,steps-1):
        x=x0+(i+.5)*going;z=(i+1)*floor/steps
        post(x,y,z,z+height)
    post(end+.20,y,floor,floor+height)

# Give only the newly authored metal its own ageing attribute; joining retains the
# existing upper rails' original face corners, normals, UVs and colours.
for ob in g.parts:
    age=ob.data.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for f in ob.data.polygons:
        for li in f.loop_indices:
            p=ob.matrix_world@ob.data.vertices[ob.data.loops[li].vertex_index].co
            age.data[li].color=(.13+.13*max(0,math.sin(p.x*1.2+p.y*.8+p.z*3)),0,0,1)
g.select(old)
for ob in g.parts:ob.select_set(True)
bpy.ops.object.join();old=bpy.context.object;g.parts=[]
tri=old.modifiers.new('New lower rail triangles','TRIANGULATE');tri.keep_custom_normals=True
bpy.ops.object.modifier_apply(modifier=tri.name)
export(old,'SM_Station_Railings',{re.sub(r'[._][0-9]{3}$','',m.name):g.MAP[re.sub(r'[._][0-9]{3}$','',m.name)[3:]] for m in old.data.materials},True)

for ob in (roof,bench,old):ob.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StationWorkshop_RefineV3.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,revision=3,ratchet_translation_cm=[-14,0,0],
    ratchet_vertices_moved=moved,lower_railing_post_bases_m=post_bases,
    ceiling_bottom_cm=320,tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('STATION_WORKSHOP_V3_AUTHORED',len(records),'MOVED_RATCHET_VERTICES',moved,flush=True)
