"""Read the actual window, barrel and masonry inputs without changing the open world."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/DetailR6'
OUT.mkdir(parents=True,exist_ok=True)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
report={'pie_active':bool(editor.get_game_world()),'meshes':{},'materials':{}}
paths=[
 '/Game/UnrealNormandy/StaticMeshes/SM_H_OldWall_Window_00A',
 '/Game/UnrealNormandy/StaticMeshes/SM_Window_Frame_00A',
 '/Game/UnrealNormandy/StaticMeshes/SM_Window_Shutter_00A',
 '/Game/UnrealNormandy/StaticMeshes/SM_Window_Shutter_01A',
 '/Game/Props/CastingStation20260926/SM_CoolingBarrel',
 '/Game/UnrealNormandy/StaticMeshes/SM_H_OldWall_00A',
 '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/LoftR3/Meshes/SM_SmithLoft_Chimney_R5']
def material(m):
 if not m or m.get_path_name() in report['materials']:return
 base=m.get_base_material()
 row={'base':base.get_path_name(),'instanced_usage':base.get_editor_property('used_with_instanced_static_meshes')}
 for prop in ('texture_parameter_values','scalar_parameter_values','vector_parameter_values'):
  try:row[prop]=[str(v) for v in m.get_editor_property(prop)]
  except Exception:pass
 report['materials'][m.get_path_name()]=row
for path in paths:
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing input '+path)
 b=mesh.get_bounding_box()
 row={'bounds_min':[b.min.x,b.min.y,b.min.z],'bounds_max':[b.max.x,b.max.y,b.max.z],'slots':[]}
 for slot in mesh.static_materials:
  m=slot.material_interface
  row['slots'].append({'slot':str(slot.material_slot_name),'material':m.get_path_name() if m else None})
  material(m)
 report['meshes'][path]=row
 if 'Chimney_R5' not in path:
  task=u.AssetExportTask();task.object=mesh;task.filename=str(OUT/(mesh.get_name()+'.fbx'))
  task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
  if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+path)
(OUT/'inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('SMITH_R6_INPUTS '+json.dumps({'pie_active':report['pie_active'],'mesh_count':len(paths)}))
