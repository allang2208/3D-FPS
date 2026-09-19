import unreal,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910')
a=unreal.load_asset('/Game/Locodrome/MAT/Locodrome_MAT');report={'mat_loaded':bool(a)}
for n in ['ControlRigBlueprintFactory','ControlRigBlueprint','RigVMController','RigHierarchyController','RigControlSettings','ControlRigSequencerEditorLibrary','EditorUtilitySubsystem']:
 c=getattr(unreal,n,None);report[n]=str(c.__doc__) if c else None
 if c:
  report[n+'_methods']={m:str(getattr(c,m).__doc__) for m in dir(c) if any(k in m for k in ['add_unit','add_control','import_bones','create_control','bake','add_link','spawn_and_register','get_controller','set_pin','compile','open_editor'])}
(O/'mat_api.json').write_text(json.dumps(report,indent=2));unreal.log('MAT_INSPECT_COMPLETE')
