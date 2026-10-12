"""Save the repaired native harness in the active editor, without running PIE."""
import importlib.util,json,shutil
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackStraps20261012'
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('Stop PIE before saving backpack straps')
data=json.loads((R/'backpack_repaired.json').read_text(encoding='utf-8'))
path=data['source'];asset=u.load_asset(path)
if not asset:raise RuntimeError('Missing active backpack '+path)
backup=P/'trash/player-presentation-retired-20261012/SourceAssets/BackpackStraps20261012/Before/SK_Jason_Backpack.uasset';backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():
    package=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    shutil.copy2(package,backup)
spec=importlib.util.spec_from_file_location('backpack_mesh_io',str(P/'Tools/ChainmailPants/save_assets.py'))
io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
G=u.GeometryScript_AssetUtils
native,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native backpack skeleton')
dm=io.dynamic(data,native)
options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write backpack harness')
subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
lod_count=subsystem.get_lod_count(asset)
if lod_count>1 and not subsystem.regenerate_lod(asset,lod_count,True,False):
    raise RuntimeError('Cannot rebuild existing backpack LODs')
u.EditorAssetLibrary.set_metadata_tag(asset,'BackpackHarnessRevision',data['revision'])
u.EditorAssetLibrary.set_metadata_tag(asset,'BackpackHarnessSource','SourceAssets/BackpackStraps20261012/backpack_repaired.json')
u.EditorAssetLibrary.set_metadata_tag(asset,'BackpackHarnessBinding','Rigid spine_03 shell; spine_03/spine_04 and limited clavicles; no arm or leg weights')
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Backpack package did not save')
(R/'saved.json').write_text(json.dumps(dict(asset=asset.get_path_name(),revision=data['revision'],
    vertices=len(data['positions']),triangles=len(data['triangles']),lods=lod_count,
    materials=data['materials'],saved=True,runtime_tested=False),indent=2),encoding='utf-8')
print('BACKPACK_HARNESS_SAVED '+asset.get_path_name(),flush=True)
