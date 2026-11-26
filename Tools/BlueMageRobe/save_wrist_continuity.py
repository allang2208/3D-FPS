"""Clone only the four active robe skin layers and restore wrist section coverage."""
import gc, hashlib, importlib.util, json, sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/WristContinuity20261020'
DEST='/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/WristContinuity20261020'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
spec=importlib.util.spec_from_file_location('robe_wrist_io',str(P/'Tools/BlueMageRobe/save_assets.py'))
io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End play before saving wrist skin partitions')
authored=json.loads((R/'authored.json').read_text())
receipt_path=R/'saved_assets.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(saved={},runtime_tested=False)
receipt['completed']=False
def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
record()
for row in authored['rows']:
    raw=Path(row['file']).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    source=u.load_asset(row['current_mesh'])
    if not source:raise RuntimeError('Current robe skin unavailable '+row['current_mesh'])
    slots=list(source.get_editor_property('materials'))
    if [str(s.material_slot_name) for s in slots]!=row['material_slots']:
        raise RuntimeError('Current skin section layout changed '+row['key'])
    folder=DEST+'/'+row['profile'];name='SK_'+row['key']+'_RobeWrist';path=folder+'/'+name
    mesh=u.load_asset(path)
    if not mesh or E.get_metadata_tag(mesh,'RobeWristSourceSHA')!=sha:
        d=json.loads(raw)
        ref,status=io.G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),
            u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read current native skin')
        dm=io.dynamic(d,ref)
        mesh=mesh or A.duplicate_asset(name,folder,source)
        options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
            new_materials=[s.material_interface for s in slots],new_material_slot_names=row['material_slots'],
            enable_recompute_normals=False,enable_recompute_tangents=True,
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,status=io.G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write wrist partition')
        if not io.S.regenerate_lod(mesh,3,True,False):raise RuntimeError('Cannot rebuild wrist LODs')
        E.set_metadata_tag(mesh,'RobeWristSourceSHA',sha)
        E.set_metadata_tag(mesh,'SourceContract',d['contract'])
        mesh.modify()
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save wrist skin '+path)
        del d,ref,dm
    receipt['saved'][row['original']]=dict(asset=mesh.get_path_name(),previous=row['current_mesh'],
        source_sha256=sha,materials_preserved=[s.material_interface.get_path_name() if s.material_interface else '' for s in slots])
    record();print('ROBE_WRIST_SAVED',row['key'],flush=True)
    del source,mesh,slots;gc.collect();u.SystemLibrary.collect_garbage()
receipt['completed']=True;record()
print('ROBE_WRIST_COMPLETE',len(receipt['saved']),flush=True)
