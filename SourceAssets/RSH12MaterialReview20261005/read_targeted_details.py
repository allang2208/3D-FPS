"""Read-only follow-up: material source paths and physical data texture export."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
p='/Game/Weapons/RSH12/QuickDrawGrip20261005/Textures/T_RSH12_QuickDrawGrip_GraphiteFrame_ORM'
t=u.load_asset(p)
r={'texture':t.get_path_name(),'dynamic_getters':[x for x in dir(u.MaterialInstanceDynamic) if 'parameter_value' in x]}
try:r['source_files']=list(t.get_editor_property('asset_import_data').extract_filenames())
except Exception as ex:r['source_read_error']=str(ex)
task=u.AssetExportTask();task.object=t;task.filename=str(O/'QuickDraw_Frame_ORM_actual.tga');task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.TextureExporterTGA()
r['exported']=u.Exporter.run_asset_export_task(task)
(O/'targeted_details.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print(json.dumps(r))
