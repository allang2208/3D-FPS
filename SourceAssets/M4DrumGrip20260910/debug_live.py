import unreal,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910')
seq=unreal.load_asset('/Game/Weapons/M4DrumGripCandidate/LS_M4_DrumGrip_reload_empty')
rig=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0].control_rig
bp=unreal.load_asset('/Game/Weapons/M4DrumGripCandidate/CR_M4_DrumGrip_MAT')
h=rig.get_hierarchy()
report={'rig_apis':{n:str(getattr(rig,n).__doc__) for n in dir(rig) if any(s in n for s in ['evaluate','execute','event','init','vm'])},'bp_apis':{n:str(getattr(bp,n).__doc__) for n in dir(bp) if any(s in n for s in ['propagate','recompile','rig_vm','generated_class'])},'transforms':{}}
for name,kind in [('hand_l',unreal.RigElementType.BONE),('hand_l_fk_ctrl',unreal.RigElementType.CONTROL),('WPN_SOCKET_Magazine',unreal.RigElementType.BONE)]:
 report['transforms'][name]=str(h.get_global_transform(unreal.RigElementKey(name=name,type=kind)))
report['tracks']=[];report['bound']=[]
for b in seq.get_bindings():
 for t in b.get_tracks():
  report['tracks'].append({'class':t.get_class().get_name(),'sections':[{'active':s.is_active(),'class':s.get_class().get_name()} for s in t.get_sections()]})
 bid=unreal.MovieSceneObjectBindingID();bid.set_editor_property('Guid',b.get_id())
 for a in unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(bid):
  c=a.skeletal_mesh_component
  report['bound'].append({'actor':a.get_path_name(),'anim_instance':str(c.get_anim_instance()),'mesh':str(c.get_editor_property('skeletal_mesh_asset')),'hand':str(c.get_socket_transform('hand_l')),'bounds':str(a.get_actor_bounds(False))})
widget=unreal.find_object(None,'/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation.L_M4RigValidation:Locodrome_MAT_C_0')
button=widget.get_editor_property('index_02_l_ctrl')
report['button_apis']=[n for n in dir(button) if not n.startswith('_') and any(s in n for s in ['click','mouse','select','parent'])]
(O/'debug_live.json').write_text(json.dumps(report,indent=2,default=str))
print('LIVE_DEBUG_DONE')

