"""Rotate only independent inventory meshes; preserve wearable and pickup sources."""
import hashlib,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackIcons20261025/FrontR1'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'plan.json');E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
rows=[]
for row in plan['items']:
 rotation=row.get('source_rotation',[0,0,0])
 if not any(rotation):continue
 source=u.load_asset(row['source']);path=row['display_asset'].split('.')[0]
 if source is None:raise RuntimeError('Missing display source '+row['source'])
 if E.does_asset_exist(path):raise RuntimeError('Preserve existing display revision '+path)
 E.make_directory(path.rsplit('/',1)[0]);target=E.duplicate_asset(source.get_path_name(),path)
 if target is None:raise RuntimeError('Could not duplicate '+path)
 slots=list(source.static_materials);lods=sub.get_lod_count(source)
 for index in range(lods):
  dm,status=G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=index))
  if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Could not read LOD '+str(index))
  u.GeometryScript_MeshTransforms.rotate_mesh(dm,u.Rotator(pitch=rotation[0],yaw=rotation[1],roll=rotation[2]))
  _,status=G.copy_mesh_to_static_mesh(dm,target,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD(lod_index=index))
  if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Could not write LOD '+str(index))
 target.set_editor_property('static_materials',slots)
 E.set_metadata_tag(target,'InventoryFacingRevision',plan['revision']);E.set_metadata_tag(target,'InventoryFacingSource',source.get_path_name());E.set_metadata_tag(target,'InventoryFacing','outer=-Y;up=+Z')
 if not E.save_loaded_asset(target,False):raise RuntimeError('Could not save '+path)
 rows.append(dict(id=row['id'],source=source.get_path_name(),asset=target.get_path_name(),rotation=rotation,lods=lods,saved=True))
 (R/'display_saved.json').write_text(json.dumps(dict(completed=True,items=rows),indent=2),encoding='utf-8')
 print('BACKPACK_INVENTORY_DISPLAY_SAVED',row['id'],path,flush=True)
