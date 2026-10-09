"""Export the three currently assigned motion sources for clothing authoring."""
import unreal as u,json
from pathlib import Path
ROOT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\FacelessReceptionist20261007\V03')
for d in ['Authoring','Delivery','Textures','MotionSources','Logs']: (ROOT/d).mkdir(parents=True,exist_ok=True)
report=[]
for role in ['idle','walk','attack']:
 path='/Game/Monsters/FacelessReceptionist/Animations/A_Receptionist_'+role
 clip=u.load_asset(path)
 task=u.AssetExportTask();task.object=clip;task.filename=str(ROOT/'MotionSources'/('A_Receptionist_'+role+'.fbx'))
 task.automated=True;task.prompt=False;task.options=u.FbxExportOption()
 task.options.set_editor_property('export_preview_mesh',False)
 task.exporter=u.AnimSequenceExporterFBX()
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Animation source export failed '+path)
 report.append({'role':role,'path':path,'file':task.filename,'seconds':clip.get_play_length()})
(ROOT/'MotionSources/sources.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RECEPTIONIST_MOTION_SOURCES_EXPORTED')
