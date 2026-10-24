"""Save new fitted meshes without changing the current worn assets or shared materials."""
import gc,hashlib,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');W=P/'SourceAssets/KaitlinCompletion20261024/Packs'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
rows=read(W/'manifest.json');receipt=W/'saved_assets.json';saved=read(receipt) if receipt.exists() else {}
G,L=u.GeometryScript_AssetUtils,u.GeometryScript_List;E=u.EditorAssetLibrary;count=0
for row in rows:
    key=row['rig']+'/'+row['item']
    if saved.get(key)==row['asset']+'.'+row['asset'].rsplit('/',1)[-1]:continue
    source_file=P/'Content'/(row['source'][6:].split('.')[0]+'.uasset')
    if hashlib.sha256(source_file.read_bytes()).hexdigest()!=row['source_sha256']:raise RuntimeError('Pack source changed '+key)
    if E.does_asset_exist(row['asset']):raise RuntimeError('Preserve unreceipted target '+row['asset'])
    source=u.load_asset(row['source']);data=read(Path(row['geometry']))
    mesh,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+key)
    u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(mesh,L.convert_array_to_vector_list([u.Vector(*v) for v in data['positions']]))
    options=u.GeometryScriptCreateNewSkeletalMeshAssetOptions();options.use_mesh_bone_proportions=True
    options.enable_recompute_normals=True;options.enable_recompute_tangents=True
    options.materials={str(m.material_slot_name):m.material_interface for m in source.materials}
    asset,status=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(mesh,source.skeleton,row['asset'],options)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Create failed '+key)
    asset.set_editor_property('physics_asset',source.physics_asset)
    if not u.FPSModularOutfitComponent.configure_outfit_lods(asset):raise RuntimeError('LOD setup failed '+key)
    if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(asset,3,True,False):raise RuntimeError('LOD generation failed '+key)
    u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'Editor.AsyncAssetCompilationFinishAll')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+key)
    saved[key]=asset.get_path_name();receipt.write_text(json.dumps(saved,indent=2),encoding='utf-8')
    print('WORK_JACKET_PACK_SAVED',key,flush=True)
    del mesh,asset,source,data;gc.collect();u.SystemLibrary.collect_garbage();count+=1
    if count>=4:break
remaining=sum(saved.get(row['rig']+'/'+row['item'])!=row['asset']+'.'+row['asset'].rsplit('/',1)[-1] for row in rows)
(P/'SourceAssets/KaitlinPlayer20261023/complete_pack_assets_status.json').write_text(json.dumps({'remaining':remaining,'complete':remaining==0}))
