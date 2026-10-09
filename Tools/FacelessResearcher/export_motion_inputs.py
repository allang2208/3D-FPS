"""Export existing Nurse authoring inputs and gameplay defaults; no playback."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V01')
bp=u.load_asset('/Game/Monsters/NurseZombie/BP_NurseZombie');cdo=u.get_default_object(bp.generated_class())
report={'blueprint':bp.get_path_name(),'clips':{},'properties':{}}
for prop in ['contact_time','contact_end','recovery_time','walk_speed','attack_range','max_health','attack_damage']:
    report['properties'][prop]=cdo.get_editor_property(prop)
mesh=cdo.get_editor_property('mesh');report['mesh_relative_location']=list(mesh.get_editor_property('relative_location').to_tuple())
report['mesh_relative_scale']=list(mesh.get_editor_property('relative_scale3d').to_tuple())
for role in ['idle','walk','attack']:
    clip=cdo.get_editor_property(role+'_clip');file=ROOT/'Motion'/('A_Nurse_'+role+'.fbx')
    task=u.AssetExportTask();task.object=clip;task.filename=str(file);task.automated=True;task.prompt=False;task.replace_identical=True
    options=u.FbxExportOption();options.ascii=False;options.export_morph_targets=False;task.options=options;task.exporter=u.AnimSequenceExporterFBX()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export '+clip.get_path_name())
    report['clips'][role]={'source':clip.get_path_name(),'file':str(file),'duration':clip.get_play_length(),'rate_scale':clip.get_editor_property('rate_scale')}
(ROOT/'nurse_source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RESEARCHER_SOURCE_MOTION_SAVED '+json.dumps(report),flush=True)
