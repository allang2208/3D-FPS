"""Apply the authored LOD ratios to UE 5.8 source models and save M27 only."""
import json
from pathlib import Path
import unreal as u

MESH='/Game/Monsters/MantisM27/ProductionV1/SK_MantisM27'
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ProductionV1')

def configure(mesh,policy):
    models=list(mesh.get_editor_property('source_models'))
    groups=policy.get_editor_property('lod_groups')
    for index,model in enumerate(models):
        model.set_editor_property('reduction_settings',groups[index].get_editor_property('reduction_settings'))
        model.set_editor_property('screen_size',groups[index].get_editor_property('screen_size'))
    mesh.set_editor_property('source_models',models)
    if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(mesh,4,True,False):
        raise RuntimeError('M27 authored distance LOD build did not finish.')

def finish():
    commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        if u.find_object(None,MESH+'.SK_MantisM27'):
            raise RuntimeError('M27 is loaded in the active editor during PIE; preserve it until PIE ends.')
        print('M27_LOD_TARGET_UNLOADED_USE_BACKGROUND',flush=True)
        return
    mesh=u.load_asset(MESH)
    configure(mesh,mesh.get_editor_property('lod_settings'))
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False): raise RuntimeError('M27 distance LOD package save failed.')
    path=ROOT/'ue_production_receipt.json'; report=json.loads(path.read_text(encoding='utf-8'))
    report['lod_triangle_ratios']=[1,.5,.2,.08]
    report['lod_screen_sizes']=[1,.45,.20,.09]
    report['lod_policy_applied_to_source_models']=True
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M27_LOD_CONFIGURATION_SAVED',flush=True)

if __name__=='__main__': finish()
