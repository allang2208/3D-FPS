"""Requested diagnosis: current mesh reference and exported imported surface."""
import unreal as u,json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/TentacleWhipV4');OUT.mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate')
cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
report={'blueprint_mesh':mesh.get_path_name(),'windup':cdo.get_editor_property('tentacle_windup_seconds'),'strike':cdo.get_editor_property('tentacle_strike_seconds'),'actors':[]}
worlds=[] if '-run=' in u.SystemLibrary.get_command_line().lower() else [u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()]
if worlds:worlds+=list(u.EditorLevelLibrary.get_game_worlds(False))
for world in worlds:
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.BoundCongregate):
        m=a.get_mesh()
        report['actors'].append({'actor':a.get_path_name(),'mesh':m.get_skeletal_mesh_asset().get_path_name(),'state':str(a.get_editor_property('net_state'))})
task=u.AssetExportTask();task.object=mesh;task.filename=str(OUT/'UE_imported_V3.fbx')
(OUT/'live_asset.json').write_text(json.dumps(report,indent=2),encoding='utf8')
task.exporter=u.SkeletalMeshExporterFBX();task.automated=True;task.prompt=False;task.replace_identical=True
options=u.FbxExportOption();options.export_morph_targets=False;options.level_of_detail=False;task.options=options
report['exported']=u.Exporter.run_asset_export_task(task)
(OUT/'live_asset.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report),flush=True)
