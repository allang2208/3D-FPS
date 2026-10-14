"""Inspect and preserve the supplied Root Crown mesh and its original binding."""
import bpy, json, hashlib, struct
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
SOURCE=ROOT/'Source/RootCrown_UserRig.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH')
points=[mesh.matrix_world@v.co for v in mesh.data.vertices]
weights={}
for vg in mesh.vertex_groups:
    entries=[(v,e.weight) for v in mesh.data.vertices for e in v.groups if e.group==vg.index and e.weight>.001]
    if entries:
        centre=sum((mesh.matrix_world@v.co*w for v,w in entries),Vector())/sum(w for v,w in entries)
        weights[vg.name]={'count':len(entries),'centroid':list(centre),'min_z':min(v.co.z for v,w in entries),'max_z':max(v.co.z for v,w in entries)}
report={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'vertices':len(points),'triangles':sum(len(p.vertices)-2 for p in mesh.data.polygons),
 'bounds':[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]],
 'rig_matrix':[list(r) for r in rig.matrix_world],'mesh_matrix':[list(r) for r in mesh.matrix_world],
 'bones':[dict(name=b.name,parent=b.parent.name if b.parent else None,head=list(b.head_local),tail=list(b.tail_local)) for b in rig.data.bones],
 'weights':weights,'actions':[a.name for a in bpy.data.actions],
 'materials':[s.material.name for s in mesh.material_slots]}
(ROOT/'Reports/source.json').write_text(json.dumps(report,indent=2),encoding='utf8')
raw=SOURCE.read_bytes();length=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+length]);offset=20+length+8
roles={'Normal':gltf['materials'][0]['normalTexture']['index'],'BaseColor':gltf['materials'][0]['pbrMetallicRoughness']['baseColorTexture']['index'],'MetallicRoughness':gltf['materials'][0]['pbrMetallicRoughness']['metallicRoughnessTexture']['index']}
for role,texture in roles.items():
    img=gltf['images'][gltf['textures'][texture]['source']];view=gltf['bufferViews'][img['bufferView']]
    start=offset+view.get('byteOffset',0)
    (ROOT/'Textures'/('T_RootCrown_'+role+'.png')).write_bytes(raw[start:start+view['byteLength']])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/RootCrown_Source.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.cycles.use_denoising=True;scene.render.resolution_x=960;scene.render.resolution_y=960;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.6,.6,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
for loc,power,size in [((-3,-4,5),500,4),((4,-1,3),320,3),((0,3,4),450,3)]:
    data=bpy.data.lights.new('Softbox','AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new('Softbox',data);scene.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(Vector((0,0,.8))-ob.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Camera');camdata.type='ORTHO';camdata.ortho_scale=2.05
cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
for name,loc in [('front',(0,-5,.9)),('back',(0,5,.9)),('side',(5,0,.9))]:
    cam.location=loc;cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(ROOT/'Previews'/('source_'+name+'.png'));bpy.ops.render.render(write_still=True)
print('ROOT_CROWN_SOURCE_READ '+json.dumps({'bones':len(report['bones']),'triangles':report['triangles'],'bounds':report['bounds']}),flush=True)
