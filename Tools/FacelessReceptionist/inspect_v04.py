import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V04')
for folder in ['Authoring','Delivery','Textures','Logs','MotionSources','Preview']:(ROOT/folder).mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/FacelessReceptionist/BP_FacelessReceptionist')
cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh')
report={'mesh':mesh.get_path_name(),'clips':{},'curve_api':{}}
for role in ['idle','walk','attack']:
 clip=cdo.get_editor_property(role+'_clip')
 report['clips'][role]={'asset':clip.get_path_name(),'duration':clip.get_play_length()}
 task=u.AssetExportTask();task.object=clip;task.filename=str(ROOT/'MotionSources'/('A_Receptionist_'+role+'.fbx'))
 task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.AnimSequenceExporterFBX()
 opts=u.FbxExportOption();opts.export_preview_mesh=False;task.options=opts
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Motion export failed '+role)
for name in ['add_curve','add_float_curve_keys','remove_curve','get_animation_curve_names','does_curve_exist']:
 fn=getattr(u.AnimationLibrary,name,None);report['curve_api'][name]=getattr(fn,'__doc__',str(fn))
report['curve_type']=str(u.RawCurveTrackTypes.__dict__)
report['materials']=[str(s.material_interface.get_path_name()) for s in mesh.materials]
report['pie_active']=u.EditorLevelLibrary.is_playing_in_editor() if hasattr(u.EditorLevelLibrary,'is_playing_in_editor') else 'unknown'
(ROOT/'live_source.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
