"""Publish corner normals to existing LODs and refine only M24 body finishes."""
import unreal as u, json, gzip, hashlib, shutil, gc
from pathlib import Path
O=Path(__file__).resolve().parent
E,G,N,L=u.EditorAssetLibrary,u.GeometryScript_AssetUtils,u.GeometryScript_Normals,u.MaterialEditingLibrary
D=json.load(gzip.open(O/'inputs.json.gz','rt',encoding='utf-8'))
patch=json.load(gzip.open(O/'corner_patch.json.gz','rt',encoding='utf-8'))
recipe=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
if not recipe['complete']:raise RuntimeError('Authoring is incomplete')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level.is_in_play_in_editor():raise RuntimeError('PIE_SAVE_BLOCKED: finish authorized PIE stop before asset save')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
R={'complete':False,'saved_meshes':[],'saved_materials':[],'gameplay_test':False,'visual_test':False,
   'positions_changed':False,'uv_changed':False,'animation_changed':False}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def disk(path):return Path(u.Paths.project_content_dir())/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def guard(path,sha):
    if path.split('.')[0] in dirty:raise RuntimeError('Unsaved target retained '+path)
    if hashlib.sha256(disk(path).read_bytes()).hexdigest()!=sha:raise RuntimeError('Concurrent target changes retained '+path)
def backup(path):
    dest=O/'Before'/(path.split('.')[0].removeprefix('/Game/')+'.uasset');dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(disk(path),dest)
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
for row in patch['meshes'].values():guard(row['path'],row['source_sha256'])
for path,row in recipe['materials'].items():guard(path,row['source_sha256'])
for row in patch['meshes'].values():backup(row['path'])
for path in recipe['materials']:backup(path)
record()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for key,row in patch['meshes'].items():
    asset=u.load_asset(row['path']);prepared=[]
    # Retain each existing source LOD and every attribute layer. Only the normal
    # overlay is authored; no reimport, replacement asset, weld or UV rewrite.
    for lod in row['lods']:
        li=lod['index']
        opts=u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,use_build_scale=False)
        dm,status=G.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),opts,u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=li))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Missing source LOD '+str(li))
        for ti,values in lod['normals'].items():
            ns=[u.Vector(*v) for v in values]
            _,valid=N.set_mesh_triangle_normals(dm,int(ti),u.GeometryScriptTriangle(vector0=ns[0],vector1=ns[1],vector2=ns[2]),True)
            if not valid:raise RuntimeError('Invalid source triangle '+ti)
        prepared.append((li,dm))
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
                  enable_remove_degenerates=False,replace_materials=False,use_original_vertex_order=True)
    for li,dm in prepared:
        _,status=G.copy_mesh_to_static_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD(lod_index=li))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Normal publication failed '+key+' '+str(li))
        bs=SM.get_lod_build_settings(asset,li)
        bs.recompute_normals=False;bs.recompute_tangents=True
        bs.use_high_precision_tangent_basis=True;bs.use_full_precision_u_vs=True
        SM.set_lod_build_settings(asset,li,bs)
    # Preserve the newly authored normals and frozen LODs while replacing the
    # degenerate tangent directions on the existing projected UV seam faces.
    if not u.M24ChassisAssetTools.bake_stock_tangent_basis(asset):
        raise RuntimeError('Tangent basis authoring failed '+key)
    E.set_metadata_tag(asset,'M24CornerNormalSource',str(O/'author.py'))
    E.set_metadata_tag(asset,'M24CornerNormalRecipe','Restore intact chassis normals; rebuild only cut/neck normals; preserve all source LOD geometry and UVs')
    save(asset)
    R['saved_meshes'].append({'path':row['path'],'lods':[li for li,_ in prepared],'tangent_basis_finalized':True,
       'sha256':hashlib.sha256(disk(row['path']).read_bytes()).hexdigest(),
       'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in asset.static_materials]})
    record();print('M24_SURFACE_MESH_SAVED',row['path'],flush=True)
    prepared.clear();gc.collect()
for path,row in recipe['materials'].items():
    mi=u.load_asset(path)
    for name,value in row['scalar'].items():L.set_material_instance_scalar_parameter_value(mi,name,value)
    L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*row['color']))
    L.update_material_instance(mi)
    E.set_metadata_tag(mi,'M24FinishRecipe',str(O/'authoring.json'))
    E.set_metadata_tag(mi,'M24FinishIntent','Dark satin body, restrained edge polish and subtle microfinish; real bevel normals restored')
    save(mi);R['saved_materials'].append({'path':path,'sha256':hashlib.sha256(disk(path).read_bytes()).hexdigest()});record()
R['complete']=True;record();print('M24_SURFACE_REFINEMENT_SAVED',len(R['saved_meshes']),len(R['saved_materials']),flush=True)
