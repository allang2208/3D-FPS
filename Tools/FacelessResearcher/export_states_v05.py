"""Export the existing Nurse special-state clips for M-05 garment authoring."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V05')
for f in ['Motion','Authoring','Delivery','Logs']:(ROOT/f).mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/FacelessResearcher/BP_FacelessResearcher');cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh')
if mesh.get_name()!='SK_FacelessResearcher_V04':raise RuntimeError('Expected accepted researcher V04 before producing additional states')
source={'blueprint':bp.get_path_name(),'base_mesh':mesh.get_path_name(),'clips':{}}
paths={'fall':'/Game/Monsters/HumanoidKnockdown/Nurse/A_Nurse_Hit_Knockback',
    'get_up':'/Game/Monsters/HumanoidKnockdown/Nurse/A_Nurse_LayToIdle',
    'prone_get_up':'/Game/Monsters/HumanoidKnockdown/Nurse/A_Nurse_ProneToIdle',
    'dizzy':'/Game/Monsters/HumanoidStun/Nurse/A_Nurse_Dizzy'}
for role,path in paths.items():
    clip=u.load_asset(path)
    if not clip:raise RuntimeError('Missing source '+path)
    file=ROOT/'Motion'/('A_Nurse_'+role+'.fbx')
    task=u.AssetExportTask();task.object=clip;task.filename=str(file);task.automated=True;task.prompt=False;task.replace_identical=True
    options=u.FbxExportOption();options.ascii=False;options.export_morph_targets=False;task.options=options;task.exporter=u.AnimSequenceExporterFBX()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+path)
    source['clips'][role]={'source':clip.get_path_name(),'duration':clip.get_play_length(),
        'rate_scale':clip.get_editor_property('rate_scale'),'file':str(file)}
(ROOT/'state_source.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
print('M05_V05_STATE_INPUTS '+json.dumps(source),flush=True)
