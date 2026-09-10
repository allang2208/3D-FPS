import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909');out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='E:/3d/3-dfps/tools/ai-gen/drum-v2-20260907/large-drum-v2.blend')
rows=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 p=[o.matrix_world@v.co for v in o.data.vertices]
 rows.append(dict(name=o.name,tris=sum(len(f.vertices)-2 for f in o.data.polygons),bounds=[[min(v[i] for v in p) for i in range(3)],[max(v[i] for v in p) for i in range(3)]],materials=[m.name for m in o.data.materials]))
(out/'source-drum.json').write_text(json.dumps(rows,indent=2));print('SOURCE_DRUM',json.dumps(rows))
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4FoldingSights20260909/M4_FoldingSights_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];r.animation_data_clear()
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
mag=next(o for o in r.children if o.type=='MESH' and 'Magazine' in o.name)
print('MAG',mag.name,len(mag.data.vertices),[(g.name) for g in mag.vertex_groups])
print('ACTIONS',[(a.name,list(a.frame_range)) for a in bpy.data.actions if a.name.startswith('M4_')])
print('MAG_BONE',[list(row) for row in r.data.bones['WPN_SOCKET_Magazine'].matrix_local])
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=700;s.render.resolution_percentage=100
for o in s.objects:o.hide_render=o not in r.children and o.name not in ['SM_M4_RearSight','SM_M4_FrontSight']
center=Vector((.05,.28,-.08));bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.6
cam.location=center+Vector((.7,-.2,.15));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
for offset in [(0.5,0,.5),(-.3,.2,.3)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(offset));bpy.context.object.data.energy=45;bpy.context.object.data.size=.6
for action_name in ['M4_reload_FingerCurl','M4_reload_empty_BoltRelease']:
 a=bpy.data.actions[action_name];r.animation_data_create();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 for f in [30,60,90,114,174]:
  s.frame_set(f);bpy.context.view_layer.update();s.render.filepath=str(out/(action_name+'-'+str(f)+'.png'));bpy.ops.render.render(write_still=True)
print('DRUM_SOURCE_INSPECTION_PASS')
