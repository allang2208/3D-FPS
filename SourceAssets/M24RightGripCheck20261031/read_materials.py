import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
manifest=json.loads((O/'outfit_geometry_manifest.json').read_text());R={}
for key in ('kaitlin_skin','ue_field_gloves_black'):
 mesh=u.load_asset(manifest[key]['path']);morphs=[m.get_name() for m in (mesh.get_editor_property('morph_targets') or [])]
 R[key]={'path':mesh.get_path_name(),'morphs':morphs}
 (O/'corrective_sources.json').write_text(json.dumps(R,indent=2))
 if morphs:
  task=u.AssetExportTask();task.object=mesh;task.filename=str(O/(key+'_with_morphs.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
  task.exporter=u.SkeletalMeshExporterFBX();task.options=u.FbxExportOption();task.options.export_morph_targets=True;task.options.level_of_detail=False
  R[key]['exported']=u.Exporter.run_asset_export_task(task)
(O/'corrective_sources.json').write_text(json.dumps(R,indent=2));print('CORRECTIVE_SOURCES',json.dumps(R),flush=True)
