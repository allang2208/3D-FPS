import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V13/Diagnosis');root.mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/FacelessSecurity/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
report={'mesh':cdo.get_editor_property('visual_mesh').get_path_name(),
        'core_clips':{p:cdo.get_editor_property(p+'_clip').get_path_name() for p in ['idle','walk','attack']},
        'pie_active':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()}
(root/'active_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
