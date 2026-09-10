import bpy,json,math,os
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).parent
SOURCE_ROOT=Path(os.environ.get('GODOT_SOURCE_ROOT','E:/3d/trash/e-drive-repositories-20260910/3d/3-dfps'))
sources={'suppressor':'akm/suppressor_01.glb','brake':'muzzle_brake/brake_01.glb','titanium_brake':'titanium_brake_candidate/titanium_brake.glb'}
report={}
for key,path in sources.items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 source_file=SOURCE_ROOT/'assets/models/attachments'/path
 assert source_file.is_file(), 'Set GODOT_SOURCE_ROOT to the restored Godot archive: '+str(source_file)
 bpy.ops.import_scene.gltf(filepath=str(source_file))
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
 points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
 lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
 report[key]={'min':list(lo),'max':list(hi),'objects':[{'name':o.name,'tris':sum(len(f.vertices)-2 for f in o.data.polygons),'materials':[m.name for m in o.data.materials if m]} for o in meshes], 'markers':{o.name:list(o.matrix_world.translation) for o in bpy.context.scene.objects if o.type=='EMPTY'}}
 s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=800;s.render.resolution_y=600;s.render.resolution_percentage=100
 s.world=bpy.data.worlds.new('Studio');s.world.color=(.12,.12,.12)
 c=(lo+hi)*.5;r=max(hi-lo)
 bpy.ops.object.camera_add(location=c+Vector((r*1.6,-r*1.5,r*.95)));cam=bpy.context.object;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=r*1.35;s.camera=cam
 for pos,power,size in [((1,-1,2),75,.4),((-1,.5,.8),45,.3)]:
  bpy.ops.object.light_add(type='AREA',location=c+Vector(pos)*r);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(c-o.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(OUT/(key+'-source.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4FoldingSights20260909/M4_FoldingSights_Editable.blend')
report['rifle']={'meshes':[{'name':o.name,'triangles':sum(len(f.vertices)-2 for f in o.data.polygons),'materials':[m.name for m in o.data.materials if m]} for o in bpy.context.scene.objects if o.type=='MESH'],'bones':{b.name:{'head':list(b.head_local),'tail':list(b.tail_local)} for o in bpy.context.scene.objects if o.type=='ARMATURE' for b in o.data.bones if any(x in b.name.lower() for x in ['muzzle','barrel','frontsight','rearsight','root'])}}
(OUT/'source-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
