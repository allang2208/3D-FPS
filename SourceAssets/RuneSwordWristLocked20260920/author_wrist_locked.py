"""Restore the preferred pre-V3 arm approach; bake proximal elbow support V4."""
import bpy,json,math,sys,ast
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).parent;ROOT=P.parents[1];PRIOR=ROOT/'SourceAssets/RuneSwordElbowRepair20260920'
sys.path.insert(0,str(P))
from wrist_locked_solver import support_elbow,smooth
SOURCE=ROOT/'SourceAssets/RuneSwordPickaxeOverhead20260920/ImpactV2/Standard/Sword_PickaxeOverhead_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RuneSword_Rig']
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
stations=json.loads((ROOT/'SourceAssets/RuneSwordPickaxeOverhead20260920/ImpactV2/authoring.json').read_text())['skin_stations']
source=bpy.data.actions['A_RuneSword_Overhead_Standard'];rig.animation_data.action=source;rig.animation_data.action_slot=source.slots[0]
scene.frame_set(0);bpy.context.view_layer.update();source_zero={b.name:b.matrix.copy() for b in rig.pose.bones}
standard=json.loads((PRIOR/'Standard_active.json').read_text());ue_zero=standard['clips']['Overhead']['samples'][0]['world']
C=Matrix.Diagonal(Vector((1,-1,1)))
K={n:(C@Quaternion(ue_zero[n]['q']).to_matrix()@C).inverted()@m.to_quaternion().to_matrix() for n,m in source_zero.items()}
# Reuse only previously established coordinate conversion/idle proximity helpers.
# Do not execute the V3 authoring, diagnostic or render entry points.
names={'from_ue','ue_matrix','to_ue','qangle','gate'}
tree=ast.parse((PRIOR/'pose_conversion.py').read_text())
module=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
exec(compile(module,str(PRIOR/'pose_conversion.py'),'exec'),globals())
targets=json.loads((P/'target_inputs.json').read_text(encoding='utf-8-sig'))
edited=[n+'_'+side for side in ('l','r') for n in ('upperarm','upperarm_twist_01','upperarm_twist_02','lowerarm','lowerarm_twist_01','lowerarm_twist_02','hand')]
manifest={'revision':'SwordWristLockedV4','base':'Pre-ElbowV3 installed snapshot / ImpactV2 overhead',
 'constraints':['original shoulder/elbow/wrist origins','original forearm direction','original hand/finger transforms','original distal forearm twist transforms'],
 'upper_roll_cap_degrees':45,'elbow_roll_correction_cap_degrees':60,'runtime_tested':False,'rendered':False,'clips':{}}
if '--seams-only' in sys.argv:manifest=json.loads((P/'authoring.json').read_text())
for variant in ('Standard','LongGrip'):
 data=standard if variant=='Standard' else json.loads((PRIOR/(variant+'_active.json')).read_text())
 out=P/variant;out.mkdir(exist_ok=True);idle=from_ue(data['clips']['Idle']['samples'][0]['world']);blend_actions=[]
 for clip,info in data['clips'].items():
  key=variant+'/'+clip+'_patch'
  if key not in targets:continue
  core=clip in ('Idle','Walk','Overhead');rows=[];previous={};blend_previous={};state={};active=0
  if '--seams-only' in sys.argv and core:continue
  action=bpy.data.actions.new('WristLockedV4_'+variant+'_'+clip) if core else None
  if action:
   action.use_fake_user=True;rig.animation_data.action=action
   scene.render.fps=round(info['intervals']/info['seconds']);scene.render.fps_base=1
  for index,row in enumerate(info['samples']):
   original=from_ue(row['world']);pose={n:m.copy() for n,m in original.items()};changed=False
   for side in ('l','r'):
    weight=1. if core else gate(original,idle,side)
    correction=support_elbow(original,rest,stations,side,state,weight)
    pose.update(correction);changed|=bool(correction)
   active+=int(changed)
   desired=to_ue(pose,row['world']);keys={}
   for n in edited:
    parent=data['parents'][n];local=desired[parent].inverted()@desired[n];p,q,s=local.decompose()
    s=(ue_matrix(row['world'][parent]).inverted()@ue_matrix(row['world'][n])).decompose()[2]
    if n in previous and q.dot(previous[n])<0:q.negate()
    previous[n]=q.copy();keys[n]={'p':list(p),'q':list(q),'s':list(s)}
   rows.append({'seconds':row['seconds'],'bones':keys})
   if action:
    scene.frame_set(index)
    for b in rig.pose.bones:
     parent=pose[b.parent.name] if b.parent else Matrix.Identity(4)
     b.matrix_basis=local_rest[b.name].inverted()@parent.inverted()@pose[b.name];b.rotation_mode='QUATERNION'
     q=b.rotation_quaternion.copy()
     if b.name in blend_previous and q.dot(blend_previous[b.name])<0:q.negate()
     b.rotation_quaternion=q;blend_previous[b.name]=q.copy()
     for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=index,group=b.name)
  patch={'asset':info['asset'],'source_sha256':targets[key]['sha256'],'intervals':info['intervals'],'seconds':info['seconds'],'edited_bones':edited,'samples':rows}
  (out/(clip+'_patch.json')).write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
  manifest['clips'][variant+'/'+clip]={'seconds':info['seconds'],'frames':len(rows),'supported_frames':active,'restored_pre_v3_approach':True}
  if action:
   for layer in action.layers:
    for strip in layer.strips:
     for bag in strip.channelbags:
      for curve in bag.fcurves:
       for k in curve.keyframe_points:k.interpolation='LINEAR'
   scene.frame_start=0;scene.frame_end=info['intervals'];scene.frame_set(0)
   bpy.ops.wm.save_as_mainfile(filepath=str(out/('Sword_'+clip+'_WristLockedV4.blend')))
   blend_actions.append({'clip':clip,'action':action.name,'fps':scene.render.fps,'end':scene.frame_end})
  print('SWORD_WRIST_LOCKED_AUTHORED '+variant+'/'+clip,flush=True)
 if blend_actions:(out/'blend_actions.json').write_text(json.dumps(blend_actions,indent=2))
(P/'authoring.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
