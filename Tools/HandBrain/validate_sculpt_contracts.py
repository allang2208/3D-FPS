"""Compare V05/V06 skinning and sampled action poses; do not change either source."""
import bpy, json, hashlib, struct
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910')
def snapshot(version):
 bpy.ops.wm.open_mainfile(filepath=str(r/version/'HandBrain_Refined_Baked.blend'))
 rig=bpy.data.objects['SK_HandBrain']; result={'meshes':{},'poses':{}}
 for name in ['HandBrain_Body','HandBrain_AttackArm','HandBrain_CrownHands','HandBrain_OralTeeth']:
  obj=bpy.data.objects[name];h=hashlib.sha256()
  for v in obj.data.vertices:
   for g in v.groups:h.update(struct.pack('<IIf',v.index,g.group,g.weight))
  result['meshes'][name]={'vertices':len(obj.data.vertices),'polygons':len(obj.data.polygons),'weights':h.hexdigest(),'groups':[g.name for g in obj.vertex_groups]}
 for action in ['Idle','Move','Attack_Slam','Attack_Howl','Death']:
  a=bpy.data.actions[action];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
  start,end=a.frame_range;frames=sorted(set(round(start+(end-start)*t/4) for t in range(5)));poses=[]
  for f in frames:
   bpy.context.scene.frame_set(f)
   poses.append([round(x,6) for b in rig.pose.bones for row in b.matrix for x in row])
  result['poses'][action]={'frames':frames,'matrices':poses}
 return result
before=snapshot('realism_v05');after=snapshot('sculpt_v06')
assert before==after,'Unexpected topology, skin weights or sampled bone action change'
report={'topology_and_skin_weights_unchanged':True,'sampled_bone_poses_unchanged':True,'actions':{k:v['frames'] for k,v in after['poses'].items()},'meshes':after['meshes']}
(r/'sculpt_v06'/'contracts_validation.json').write_text(json.dumps(report,indent=2))
print('SCULPT_CONTRACTS_PASS')
