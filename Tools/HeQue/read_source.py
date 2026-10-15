"""Preserve and inspect the user's reduced, lightly rigged HeQue source."""
import bpy, json, hashlib, shutil, math
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/RigV01')
SOURCE=Path('C:/Users/allan/Downloads/Meshy_AI_Character_output (4).glb')
for folder in ('Inputs','Authoring','Export','Textures','Records','Inspection'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
copy=ROOT/'Inputs/HeQue_user_rig.glb'
if not copy.exists():shutil.copy2(SOURCE,copy)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(copy))
report={'source':str(SOURCE),'sha256':hashlib.sha256(copy.read_bytes()).hexdigest(),'meshes':[],'rigs':[]}
for ob in bpy.context.scene.objects:
    if ob.type=='ARMATURE':
        report['rigs'].append({'name':ob.name,'matrix':[list(r) for r in ob.matrix_world],
            'bones':[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in ob.data.bones]})
    if ob.type!='MESH':continue
    pts=[ob.matrix_world@v.co for v in ob.data.vertices]
    groups={g.name:{'n':0,'weight':0.,'center':[0.,0.,0.]} for g in ob.vertex_groups}
    missing=0;maxinf=0
    for v,p in zip(ob.data.vertices,pts):
        valid=[e for e in v.groups if e.weight>1e-6];maxinf=max(maxinf,len(valid));missing+=not valid
        for e in valid:
            row=groups[ob.vertex_groups[e.group].name];row['n']+=1;row['weight']+=e.weight
            for k in range(3):row['center'][k]+=p[k]*e.weight
    for row in groups.values():
        if row['weight']:row['center']=[x/row['weight'] for x in row['center']]
    report['meshes'].append({'name':ob.name,'vertices':len(pts),'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons),
        'bounds':[[min(p[k] for p in pts) for k in range(3)],[max(p[k] for p in pts) for k in range(3)]],
        'materials':[m.name for m in ob.data.materials],'matrix':[list(r) for r in ob.matrix_world],
        'missing':missing,'max_influences':maxinf,'groups':groups})
report['actions']=[dict(name=a.name,range=list(a.frame_range)) for a in bpy.data.actions]
report['images']=[dict(name=i.name,size=list(i.size),path=i.filepath) for i in bpy.data.images]
(ROOT/'Records/source.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_source.blend'))
# The user explicitly requested model/rig inspection. These images are of the
# supplied asset, not a new concept generation or an engine acceptance render.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Inspection');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.5,.5,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
meshes=[o for o in scene.objects if o.type=='MESH'];pts=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
lo=Vector(tuple(min(p[k] for p in pts) for k in range(3)));hi=Vector(tuple(max(p[k] for p in pts) for k in range(3)))
centre=(lo+hi)*.5;height=hi.z-lo.z
for loc,power in [((-3,-4,5),500),((4,-1,3),300),((0,3,4),400)]:
    data=bpy.data.lights.new('Softbox','AREA');data.energy=power;data.shape='DISK';data.size=4
    ob=bpy.data.objects.new('Softbox',data);scene.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(centre-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('InspectionCamera');data.type='ORTHO';data.ortho_scale=height*1.15
cam=bpy.data.objects.new('InspectionCamera',data);scene.collection.objects.link(cam);scene.camera=cam
for name,direction in [('front',(0,-1,0)),('back',(0,1,0)),('left',(1,0,0))]:
    cam.location=centre+Vector(direction)*height*3
    cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(ROOT/'Inspection'/('source_'+name+'.png'));bpy.ops.render.render(write_still=True)
print('HEQUE_SOURCE '+json.dumps({'meshes':[{k:v for k,v in m.items() if k!='groups'} for m in report['meshes']], 'bones':[len(r['bones']) for r in report['rigs']],'actions':report['actions']}),flush=True)
