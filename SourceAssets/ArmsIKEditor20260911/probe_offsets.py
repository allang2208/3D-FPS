import unreal,json
from pathlib import Path
E=unreal.LevelSequenceEditorBlueprintLibrary;E.set_current_time(0)
seq=E.get_current_level_sequence();r=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0].control_rig;h=r.get_hierarchy()
d={'api':{n:str(getattr(h,n).__doc__) for n in dir(h) if 'control_value' in n or 'control_offset' in n},'nodes':{}}
for n in ['SK_M4_Infima','VM_Root','root','pelvis','spine_01','upperarm_l','hand_l']:
 k=unreal.RigElementKey(type=unreal.RigElementType.CONTROL,name=n+'_fk_ctrl');b=unreal.RigElementKey(type=unreal.RigElementType.BONE,name=n)
 d['nodes'][n]={'ctrl_local':str(h.get_local_transform(k)),'ctrl_initial_local':str(h.get_local_transform(k,True)),'bone_initial_local':str(h.get_local_transform(b,True)),'ctrl_global':str(h.get_global_transform(k)),'bone_global':str(h.get_global_transform(b)),'value':str(unreal.ControlRigSequencerLibrary.get_local_control_rig_euler_transform(seq,r,k.name,unreal.FrameNumber(0)))}
Path(__file__).with_suffix('.json').write_text(json.dumps(d,indent=2))
