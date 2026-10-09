"""Read active reaction authoring inputs, without running animation or PIE."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V02')
for folder in ['Motion','Authoring','Delivery','Logs']:(ROOT/folder).mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/FacelessResearcher/BP_FacelessResearcher')
cdo=u.get_default_object(bp.generated_class());combat=cdo.get_editor_property('combat')
mesh=cdo.get_editor_property('visual_mesh')
report={'blueprint':bp.get_path_name(),'mesh':mesh.get_path_name(),
        'skeleton':mesh.get_editor_property('skeleton').get_path_name(),
        'clips':{},'runtime_tested':False}
for role in ['idle','walk','attack']:
    clip=cdo.get_editor_property(role+'_clip')
    report['clips'][role]={'source':clip.get_path_name(),'duration':clip.get_play_length()}
for role,prop in [('hit','hit_clip'),('dizzy','dizzy_clip')]:
    clip=combat.get_editor_property(prop)
    if not clip:
        report['clips'][role]=None
        continue
    file=ROOT/'Motion'/('A_Researcher_source_'+role+'.fbx')
    task=u.AssetExportTask();task.object=clip;task.filename=str(file);task.automated=True;task.prompt=False;task.replace_identical=True
    options=u.FbxExportOption();options.ascii=False;options.export_morph_targets=False;task.options=options;task.exporter=u.AnimSequenceExporterFBX()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Reaction source export failed '+clip.get_path_name())
    report['clips'][role]={'source':clip.get_path_name(),'duration':clip.get_play_length(),
        'rate_scale':clip.get_editor_property('rate_scale'),'skeleton':clip.get_editor_property('skeleton').get_path_name(),'file':str(file)}
if not report['clips']['hit']:raise RuntimeError('Researcher has no configured reaction clip')
(ROOT/'reaction_source.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('RESEARCHER_REACTION_INPUT_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
