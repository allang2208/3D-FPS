"""Reuse the city, add supported waterfront tiers, export only new detail batches."""
import bpy,json,ast,math,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'RefinementV7/BayLandmarks_Source.blend'))
scene=bpy.context.scene
# The actual main-map city retains its dimensions and all attachments.
for ob in scene.objects:
    if ob.type=='MESH' and (ob.name.startswith(('City_','Quay_','Landmark_','Far')) or ob.name=='Harbor'):
        ob.location.y+=AUTHOR_SHIFT_Y
groups={};ATLAS_METRES=(12.,12.);mats={m.name:m for m in bpy.data.materials}
tree=ast.parse((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/author_scene.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('face','box','beam')],type_ignores=[]),'reused_architecture_geometry','exec'),globals())
baseface=face
def face(g,vs,mat='Frame',uv=None):
    if uv is None:
        n=(Vector(vs[1])-Vector(vs[0])).cross(Vector(vs[2])-Vector(vs[0]));dominant=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3) if i!=dominant]
        uv=[(v[axes[0]]/12,v[axes[1]]/12) for v in vs]
    baseface(g,vs,mat,uv)

def strip(g,a,b,inland,lo,hi,z0,z1,mat):
    pts=[a+inland*lo,b+inland*lo,b+inland*hi,a+inland*hi]
    face(g,[(p.x,p.y,z1) for p in pts],mat)
    for i in range(4):
        p,q=pts[i],pts[(i+1)%4];face(g,[(p.x,p.y,z0),(q.x,q.y,z0),(q.x,q.y,z1),(p.x,p.y,z1)],mat)
    face(g,[(p.x,p.y,z0) for p in pts[::-1]],mat)

# Three contiguous material batches; real slab edges and recessed floodwall joints.
for i in range(1,6):
    a=Vector((*SHORE[i],0));b=Vector((*SHORE[i+1],0));a.y+=AUTHOR_SHIFT_Y;b.y+=AUTHOR_SHIFT_Y
    tangent=(b-a).normalized();inland=Vector((-tangent.y,tangent.x,0));g='Promenade_'+str((i-1)//2)
    strip(g,a,b,inland,-9,1,1.8,3.6,'Stone')
    strip(g,a,b,inland,-3,1,3.6,4.35,'Frame')
    strip(g,a,b,inland,-.8,1,4.35,5.65,'Stone')
    count=max(1,round((b-a).length/42))
    for j in range(count):
        # Separate broad bars instead of a single uninterrupted luminous horizon.
        p=a+(b-a)*(j+.12)/count;q=a+(b-a)*(j+.75)/count
        strip(g,p,q,inland,-3.08,-2.96,3.85,4.22,'Neon0' if j%3 else 'WarmLight')
        p=a+(b-a)*(j+.85)/count
        beam(g,(p.x,p.y,1.9),(p.x,p.y,5.65),.8,1.4,'Frame')

# Existing ferry platforms receive supported lower piers and broad folded canopies.
for i,(x,y) in enumerate([(-760,1080),(-270,1160),(200,1280)]):
    y+=AUTHOR_SHIFT_Y;g='FerryDetail'
    box(g,(x,y-110,2.7),(54,48,2.4),'Stone')
    for dx in (-23,23):
        for dy in (-126,-94):
            box(g,(x+dx,y+dy,-2),(2.2,2.2,8),'Frame')
    # Pedestrian connector meets the existing platform at y-85.5.
    box(g,(x,y-86,3.7),(24,5,1.2),'Stone')
    for dx in (-24,24):
        for dy in (-125,-96):beam(g,(x+dx,y+dy,3.9),(x+dx,y+dy,14.5),.85,.85,'Frame')
    box(g,(x,y-111,14.8),(53,34,1.1),'Frame')
    for j in range(7):
        xx=x-24+j*8
        beam(g,(xx,y-128,14.8),(xx,y-111,17.2),.65,.65,'Frame')
        beam(g,(xx,y-111,17.2),(xx,y-94,14.8),.65,.65,'Frame')
    box(g,(x,y-128.65,14.65),(47,.45,.45),'WarmLight')
    for dx in (-14,14):box(g,(x+dx,y-118,4.65),(8,2.4,1.5),'Frame')

records=[];export=R/'Meshes';export.mkdir(exist_ok=True)
for name,data in groups.items():
    me=bpy.data.meshes.new(name);me.from_pydata(data['v'],[],data['f']);me.update();ob=bpy.data.objects.new('AP15_'+name,me);scene.collection.objects.link(ob)
    order=list(dict.fromkeys(data['m']))
    for key in order:me.materials.append(mats[key])
    uv=me.uv_layers.new(name='ArchitecturalUV')
    for poly,key,coords in zip(me.polygons,data['m'],data['uv']):
        poly.material_index=order.index(key)
        for li,co in zip(poly.loop_indices,coords):uv.data[li].uv=co
    clone=ob.copy();clone.data=me.copy();scene.collection.objects.link(clone);clone.name='SM_AP15_'+name
    for v in clone.data.vertices:v.co=((-v.co.x+10)*1.25,-v.co.y*1.25,(v.co.z-90)*1.25)
    bpy.ops.object.select_all(action='DESELECT');clone.select_set(True);bpy.context.view_layer.objects.active=clone
    mod=clone.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    fbx=export/(clone.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    records.append(dict(key=name,name=clone.name,fbx=str(fbx),triangles=len(clone.data.polygons),materials=order))
    bpy.data.objects.remove(clone,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'CloserBay_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(meshes=records,rigid_shift_metres=WORLD_SHIFT_Y,central_river_before_m=(1230-36)*1.25,central_river_after_m=(615-36)*1.25,building_geometry_resized=False),indent=2),encoding='utf8')
print('AP15_WATERFRONT_AUTHORED',sum(r['triangles'] for r in records))
