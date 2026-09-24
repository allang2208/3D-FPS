"""Install the direct Godot-to-Meshy run, retaining every other action."""
import json,shutil,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
from install_canine_run import main as install_run

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedDogMeshy20260924/GodotRunFitV2')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('End PIE before saving the fitted Godot run')
bp=u.load_asset('/Game/Monsters/InfectedDog/BP_InfectedDog')
dataset=u.get_default_object(bp.generated_class()).get_editor_property('animation_set')
if dataset.get_path_name()!='/Game/Monsters/InfectedDog/MeshyV2/DA_InfectedDogMeshy_AnimationSet.DA_InfectedDogMeshy_AnimationSet':
    raise RuntimeError('Active infected-dog animation set changed')
before=ROOT/'binding_before.json'
if not before.exists():
    data={'blueprint':bp.get_path_name(),'dataset':dataset.get_path_name(),
          'mesh':dataset.get_editor_property('reference_mesh').get_path_name(),'actions':{}}
    for name in ['walk_speed','run_speed','run_blend_start_ratio','run_blend_full_ratio',
                 'full_turn_yaw_rate','walk_phase_offset','run_phase_offset']:
        data[name]=dataset.get_editor_property(name)
    for role,action in dataset.get_editor_property('actions').items():
        row={name:str(action.get_editor_property(name)) for name in
             ['loop','hold_last_pose','terminal','next_action','blend_seconds','play_rate','contact_start_seconds','contact_end_seconds']}
        clip=action.get_editor_property('sequence');row['sequence']=clip.get_path_name() if clip else None
        data['actions'][str(role)]=row
    before.write_text(json.dumps(data,indent=2),encoding='utf-8')
    shutil.copy2('D:/FPS3D/FPSGAME/Content/Monsters/InfectedDog/MeshyV2/DA_InfectedDogMeshy_AnimationSet.uasset',
                 ROOT/'DA_InfectedDogMeshy_AnimationSet.before.uasset')
report=install_run(ROOT=ROOT,DEST='/Game/Monsters/InfectedDog/MeshyV2/GodotRunFitV2',
                   NAME='A_InfectedDogMeshy_GodotRunFitV2',REVISION='DirectGodotCanineFitV2-20260924')
report['offline_diagnostic_rendered']=(ROOT.parent/'RunBloodDiagnosis/blender_godot_fit.json').exists()
report['preview_rendered']=report['offline_diagnostic_rendered']
report['gameplay_rendered']=False
(ROOT/'installation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
