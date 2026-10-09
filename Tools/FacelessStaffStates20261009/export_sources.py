"""Export the existing common reactions, with no asset changes or PIE changes."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessStaffStates20261009')
source={'clips':{},'characters':{}}
paths={'hit':'/Game/Monsters/AI/A_Nurse_Hit','fall':'/Game/Monsters/HumanoidKnockdown/Nurse/A_Nurse_Hit_Knockback',
'get_up':'/Game/Monsters/HumanoidKnockdown/Nurse/A_Nurse_LayToIdle','prone_get_up':'/Game/Monsters/HumanoidKnockdown/Nurse/A_Nurse_ProneToIdle','dizzy':'/Game/Monsters/HumanoidStun/Nurse/A_Nurse_Dizzy'}
for role,path in paths.items():
    clip=u.load_asset(path);file=ROOT/'Motion'/('A_Nurse_'+role+'.fbx')
    task=u.AssetExportTask();task.object=clip;task.filename=str(file);task.automated=True;task.prompt=False;task.replace_identical=True
    options=u.FbxExportOption();options.ascii=False;options.export_morph_targets=False;task.options=options;task.exporter=u.AnimSequenceExporterFBX()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+path)
    source['clips'][role]={'source':clip.get_path_name(),'duration':clip.get_play_length(),'rate_scale':clip.get_editor_property('rate_scale'),'file':str(file)}
for who,version in [('Security','V11'),('Receptionist','V04')]:
    bp=u.load_asset('/Game/Monsters/Faceless'+who+'/BP_Faceless'+who);cdo=u.get_default_object(bp.generated_class())
    mesh=cdo.get_editor_property('visual_mesh')
    if mesh.get_name()!='SK_Faceless'+who+'_'+version:raise RuntimeError('Source revision changed '+who)
    source['characters'][who]={'blueprint':bp.get_path_name(),'mesh':mesh.get_path_name(),'skeleton':mesh.get_editor_property('skeleton').get_path_name(),
        'core_clips':{r:cdo.get_editor_property(r+'_clip').get_path_name() for r in ['idle','walk','attack']}}
(ROOT/'source.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
print('FACELESS_STAFF_INPUTS_EXPORTED '+str(ROOT/'source.json'))