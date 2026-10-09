"""Export the researcher's actual four active motion inputs for waist tailoring."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V03')
for folder in ['Motion','Authoring','Delivery','Logs']:(ROOT/folder).mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/FacelessResearcher/BP_FacelessResearcher')
cdo=u.get_default_object(bp.generated_class());combat=cdo.get_editor_property('combat')
mesh=cdo.get_editor_property('visual_mesh')
report={'blueprint':bp.get_path_name(),'mesh':mesh.get_path_name(),'clips':{},'runtime_tested':False}
for role in ['idle','walk','attack','hit']:
    clip=combat.get_editor_property('hit_clip') if role=='hit' else cdo.get_editor_property(role+'_clip')
    file=ROOT/'Motion'/('A_Researcher_source_'+role+'.fbx')
    task=u.AssetExportTask();task.object=clip;task.filename=str(file);task.automated=True;task.prompt=False;task.replace_identical=True
    options=u.FbxExportOption();options.ascii=False;options.export_morph_targets=False;task.options=options;task.exporter=u.AnimSequenceExporterFBX()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Source export failed '+clip.get_path_name())
    report['clips'][role]={'source':clip.get_path_name(),'duration':clip.get_play_length(),
        'rate_scale':clip.get_editor_property('rate_scale'),'file':str(file)}
(ROOT/'waist_source.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('RESEARCHER_WAIST_INPUTS_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
