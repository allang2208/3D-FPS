"""Requested left-elbow and wrist inspection using the actual native V7 skin."""
import bpy,json,gzip,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
with gzip.open(S/'M870ReloadWrist20261016/native_arms.json.gz','rt',encoding='utf-8') as f:skin=json.load(f)
report={}
for label,folder,blend in [('before','M870TriggerGrip20261016','M870_TriggerGrip_Editable.blend'),('after','M870LeftArm20261016','M870_LeftArm_Editable.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(S/folder/blend),use_scripts=False);r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
 auth=json.loads((S/folder/'authoring.json').read_text());a=bpy.data.actions[auth['clips']['idle']['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
 for ob in list(s.objects):
  if ob.type in ('CAMERA','LIGHT') or (ob.type=='MESH' and ('V7' in ob.name or 'BareArm' in ob.name)):bpy.data.objects.remove(ob,do_unlink=True)
 faces=[f for f in skin['faces'] if any(sum(w for n,w in skin['weights'][i].items() if n.endswith('_l'))>.5 for i in f)]
 me=bpy.data.meshes.new('Native left skin');me.from_pydata([(v[0]/100,-v[1]/100,v[2]/100) for v in skin['vertices']],[],faces);me.update();arm=bpy.data.objects.new('NativeLeftArm',me);s.collection.objects.link(arm)
 for p in me.polygons:p.use_smooth=True
 for n in {n for w in skin['weights'] for n in w}:arm.vertex_groups.new(name=n)
 for i,w in enumerate(skin['weights']):
  for n,v in w.items():arm.vertex_groups[n].add([i],v,'REPLACE')
 arm.parent=r;arm.matrix_parent_inverse=Matrix.Identity(4);arm.matrix_basis=Matrix.Identity(4);arm.modifiers.new('Native skin','ARMATURE').object=r
 for ob in s.objects:
  if ob.type=='MESH':ob.hide_render=ob.name=='M870_ReloadShell';ob.color=(.58,.37,.25,1) if ob==arm else (.1,.12,.14,1)
 cam=bpy.data.objects.new('LeftArmInspection',bpy.data.cameras.new('LeftArmInspection'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO'
 s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=900;s.render.resolution_y=650;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
 s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD'
 if not s.world:s.world=bpy.data.worlds.new('Inspection')
 s.world.color=(.055,.055,.055)
 p={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};e=p['lowerarm_l'].translation;h=p['hand_l'].translation
 for name,center,delta,size in [('overview',(e+h)*.5,Vector((-.3,-.4,.3)),.52),('elbow',e,Vector((-.10,.05,.25)),.24),('wrist',h,Vector((-.15,-.12,.22)),.22)]:
  cam.data.ortho_scale=size;cam.location=center+delta;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{label}_{name}.png');bpy.ops.render.render(write_still=True)
 rf=rest['hand_l'].translation-rest['lowerarm_l'].translation;hd=(p['hand_l']@rest['hand_l'].inverted()).to_quaternion();fore=h-e
 report[label]={'wrist_axis_bend_deg':math.degrees((hd@rf).angle(fore)),'distal_station_to_hand_deg':math.degrees((p['lowerarm_twist_01_l']@rest['lowerarm_twist_01_l'].inverted()).to_quaternion().rotation_difference(hd).angle),'hand_world':[list(v) for v in p['hand_l']],'elbow':list(e),'shoulder':list(p['upperarm_l'].translation)}
(O/'idle_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M870_LEFT_IDLE_INSPECTED',flush=True)
