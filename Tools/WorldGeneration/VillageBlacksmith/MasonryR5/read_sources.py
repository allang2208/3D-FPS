"""Read the existing house masonry as a geometry/material donor for the chimney."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/MasonryR5';OUT.mkdir(parents=True,exist_ok=True)
mesh=u.load_asset('/Game/UnrealNormandy/StaticMeshes/SM_H_OldWall_00A')
task=u.AssetExportTask();task.object=mesh;task.filename=str(OUT/'HouseWallDonor.fbx')
task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export house stone source')
report={'mesh':mesh.get_path_name(),'materials':[]}
for slot in mesh.static_materials:
 material=slot.material_interface
 report['materials'].append({'slot':str(slot.material_slot_name),'material':material.get_path_name() if material else None})
(OUT/'source-materials.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('SMITH_MASONRY_SOURCE_EXPORTED')
