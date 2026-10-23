import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpacksReview20261021'
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
path=cfg['outfits']['ue_portable_backpack']['world_static_mesh'];asset=u.load_asset(path)
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read current ALICE mesh')
_,points,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
v=u.GeometryScript_List.convert_vector_list_to_array(points)
data=dict(asset=path,positions=[[p.x,p.y,p.z] for p in v],triangles=dm.get_triangle_count(),
          materials=[dict(slot=str(m.material_slot_name),asset=m.material_interface.get_path_name()) for m in asset.static_materials],
          lod_count=subsystem.get_lod_count(asset),bounds=str(asset.get_bounds()))
(R/'alice_ue_before.json').write_text(json.dumps(data),encoding='utf-8')
print('ALICE_ACTUAL_ASSET',path,dm.get_triangle_count(),data['lod_count'])
