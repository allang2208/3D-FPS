"""Read current editor state and the exact existing house/forge interfaces for authoring."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3';OUT.mkdir(parents=True,exist_ok=True)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_editor_world() if editor else None
report={'project':u.Paths.project_dir(),'world':world.get_path_name() if world else None,
 'pie':bool(editor and editor.get_game_world()),'dirty_maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],'meshes':{}}
paths=['/Game/UnrealNormandy/StaticMeshes/'+n for n in ['SM_H_OldWall_00A','SM_H_OldWall_Window_00A','SM_Window_Frame_00A','SM_Window_Shutter_00A','SM_Window_Shutter_01A','SM_WoodenFloor_00A','SM_Roof_00A','SM_RoofEnd_00A']]
paths+=['/Game/Props/CastingStation20260926/SM_CastingStation','/Game/Props/CastingStation20260926/SM_CoolingBarrel']
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
for entry in palette.components:
    if str(entry.id)=='casting_station':report['station_mesh']=entry.mesh.get_path_name();paths.append(report['station_mesh'])
for path in sorted(set(paths)):
    m=u.load_asset(path)
    if not m:raise RuntimeError(path)
    b=m.get_bounding_box();report['meshes'][path]={'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z],
       'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in m.static_materials]}
(OUT/'source-interfaces.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('LOFT_R3_SOURCES '+json.dumps({'pie':report['pie'],'dirty_maps':report['dirty_maps'],'meshes':len(report['meshes'])}))
