"""Save M16's common neutral left-digit bind and matching geometry in place."""
import hashlib, json, shutil
from pathlib import Path
import unreal as u

P=Path(u.Paths.project_dir()).resolve()
O=Path(__file__).parent
G,Q=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries
E=u.EditorAssetLibrary
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
RECEIPT=O/'installed.json'
saved=json.loads(RECEIPT.read_text()) if RECEIPT.exists() else {}

def disk(path):
    return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish the running game before saving the M16 neutral hand bind')

# Authoring inputs describe positions before the unsuccessful DQ repair, while
# expected package hashes refer to the packages currently saved in the project.
manifest=json.loads((O/'Authored/authoring.json').read_text(encoding='utf-8'))
bind=json.loads(Path(manifest['reference']).read_text(encoding='utf-8'))
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
patches=[]
for entry in manifest['patches']:
    patch=json.loads(Path(entry['patch']).read_text(encoding='utf-8'))
    path=patch['source']
    if path.split('.')[0] in dirty:
        raise RuntimeError('Preserve unsaved asset '+path)
    expected=saved.get(path,{}).get('after_sha256',patch['source_sha256'])
    if sha(disk(path))!=expected:
        raise RuntimeError('M16 input changed after neutral-bind authoring: '+path)
    patches.append(patch)

for patch in patches:
    path=patch['source']
    if path in saved: continue
    asset=u.load_asset(path)
    if not asset: raise RuntimeError('Missing M16 mesh '+path)
    backup=O/'Before/Packages'/disk(path).relative_to(P/'Content')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists(): shutil.copy2(disk(path),backup)
    skeleton_path=asset.skeleton.get_path_name()
    skeleton_hash=sha(disk(skeleton_path))
    before_materials=[(str(s.material_slot_name),s.material_interface.get_path_name() if s.material_interface else None) for s in asset.materials]
    modifier=u.SkeletonModifier()
    if not modifier.set_skeletal_mesh(asset): raise RuntimeError('Cannot load reference bind '+path)
    names=[];transforms=[]
    for bone in bind['local_transforms']:
        names.append(bone['name'])
        transform=u.Transform()
        transform.translation=u.Vector(*bone['translation'])
        transform.rotation=u.Quat(*bone['rotation_xyzw'])
        transform.scale3d=u.Vector(*bone['scale'])
        transforms.append(transform)
    if not modifier.set_bones_transforms(names,transforms,True):
        raise RuntimeError('Cannot write neutral finger reference pose '+path)
    if not modifier.commit_skeleton_to_skeletal_mesh():
        raise RuntimeError('Cannot commit neutral finger inverse binding '+path)
    # Copy AFTER changing the mesh ref pose so bone attributes agree with the
    # new inverse bind. Transform-only edits keep the shared USkeleton intact.
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot read '+path)
    _,triangles,_=Q.get_all_triangle_indices(dm,False)
    ts=u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    if patch['arm_ids'] is not None:
        ids=sorted({v for i,t in enumerate(ts)
            if u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] in patch['arm_ids']
            for v in (t.x,t.y,t.z)})
    else:
        _,positions,_=Q.get_all_vertex_positions(dm,False)
        ids=list(range(len(u.GeometryScript_List.convert_vector_list_to_array(positions))))
    if len(ids)!=patch['vertex_count']:
        raise RuntimeError('M16 vertex mapping changed: '+path)
    changed=set()
    for edit in patch['vertex_edits']:
        vi=ids[edit['index']]
        _,valid=u.GeometryScript_MeshEdits.set_vertex_position(dm,vi,u.Vector(*edit['position']),True)
        if not valid: raise RuntimeError('Cannot set M16 vertex '+str(vi))
        changed.add(vi)
    affected=[i for i,t in enumerate(ts) if any(v in changed for v in (t.x,t.y,t.z))]
    _,selection=u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(dm,affected,u.GeometryScriptMeshSelectionType.TRIANGLES)
    u.GeometryScript_Normals.recompute_normals_for_mesh_selection(dm,selection,u.GeometryScriptCalculateNormalsOptions())
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=False,
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot commit M16 geometry '+path)
    lod_count=S.get_lod_count(asset)
    for lod in range(lod_count):
        settings=S.get_lod_build_settings(asset,lod)
        settings.set_editor_property('use_full_precision_u_vs',True)
        S.set_lod_build_settings(asset,lod,settings)
    if lod_count>1 and not S.regenerate_lod(asset,lod_count,True,False):
        raise RuntimeError('Cannot produce M16 neutral-bind LODs '+path)
    E.set_metadata_tag(asset,'M16LeftHandBindRepair','20261002; common V7 neutral left digit mesh bind; native M16 animation skeleton')
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):
        raise RuntimeError('Cannot save '+path)
    saved[path]=dict(before_sha256=patch['source_sha256'],after_sha256=sha(disk(path)),backup=str(backup),
        edited_vertex_count=len(changed),neutral_reference_bones=names,skeleton=skeleton_path,
        skeleton_sha256=skeleton_hash,material_slots=before_materials,animation_assets_changed=False,runtime_tested=False)
    RECEIPT.write_text(json.dumps(saved,indent=2),encoding='utf-8')
    u.log('CLOVEN_M16_NEUTRAL_BIND_SAVED '+path)
u.log('CLOVEN_M16_NEUTRAL_BIND_INSTALL_COMPLETE '+str(len(saved)))
