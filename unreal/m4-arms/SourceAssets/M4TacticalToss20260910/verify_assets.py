import unreal,json
from pathlib import Path
O=Path(__file__).parent;lib=unreal.AnimPoseExtensions;math=unreal.MathLibrary;mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=unreal.AnimDataEvalType.COMPRESSED;report={}
for clip,end in [('reload',126)]:
 a=unreal.load_asset('/Game/Weapons/M4TacticalTossFinal/A_M4_HK416_'+clip);assert a and a.get_editor_property('number_of_sampled_keys')==end*8+1
 held=None;grip=None;hook=None;d=g=h=0
 for k in range(end*16+1):
  f=k/16;p=lib.get_anim_pose_at_time(a,f/60,opt)
  bone=lambda n:lib.get_bone_pose(p,n,unreal.AnimPoseSpaces.WORLD)
  relative=lambda parent,child:math.inverse_transform_location(bone(parent),bone(child).translation)
  pos=relative('WPN_root','hand_l' if clip=='equip_charge' else 'hand_r')
  if held is None:held=pos
  d=max(d,pos.distance(held)*1000)
  if clip!='equip_charge' and ((43<=f<=88) if clip=='reload_empty' else (61<=f<=98)):
   pos=relative('WPN_SOCKET_Magazine','hand_l')
   if grip is None:grip=pos
   g=max(g,pos.distance(grip)*1000)
  if clip=='equip_charge' and 12<=f<=19:
   pos=relative('WPN_ChargingHandle','hand_r')
   if hook is None:hook=pos
   h=max(h,pos.distance(hook)*1000)
 report[clip]={'keys':a.get_editor_property('number_of_sampled_keys'),'duration':a.get_play_length(),'samples_960hz':end*16+1,'held_drift_mm':d,'grasp_drift_mm':g,'hook_drift_mm':h}
 assert max(d,g,h)<.7,report[clip]
(O/'ue_saved_contract.json').write_text(json.dumps(report,indent=2));unreal.log('M4_SAVED_CONTRACT_PASS')
