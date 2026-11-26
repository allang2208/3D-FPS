"""Save three authored LODs against the installed glove's original reference rig."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import unreal as u

sys.path.insert(0,str(Path(__file__).parent))
from native_glove_profile import P,R,MODEL_NAME,SOURCE_FILE
folder = '/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/NativeGloveR1'
name = MODEL_NAME
source_file = SOURCE_FILE
d = json.loads(source_file.read_text())
g = u.GeometryScript_AssetUtils
e = u.EditorAssetLibrary
base = u.load_asset(d['source'])
source,status = g.copy_mesh_from_skeletal_mesh(base,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Missing glove skeleton')
spec=importlib.util.spec_from_file_location('native_outfit_mesh',str(P/'Tools/ChainmailPants/save_assets.py'))
io=importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)
dm=io.dynamic(d,source)
asset = u.load_asset(folder+'/'+name) if e.does_asset_exist(folder+'/'+name) else u.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,folder,base)
materials=[u.load_asset(m) for m in d['materials']]
if not all(materials):
    raise RuntimeError('Glove material not mounted')
options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,new_material_slot_names=d['material_slots'],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
for lod in range(3):
    options.set_editor_property('defer_mesh_post_edit_change',lod<2)
    _,status=g.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD(lod_index=lod))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError(f'LOD {lod} save failed')
provenance=u.new_object(u.AssetImportData,outer=asset)
provenance.scripted_add_filename(str(source_file),0,'Native shotgun glove source')
asset.set_editor_property('asset_import_data',provenance)
asset.set_editor_property('physics_asset',None)
sha=hashlib.sha256(source_file.read_bytes()).hexdigest()
e.set_metadata_tag(asset,'CombatSourceSHA',sha)
e.set_metadata_tag(asset,'CombatRevision','NativeGloveR1')
if not e.save_loaded_asset(asset,False):
    raise RuntimeError('Glove package save failed')
receipt=dict(asset=asset.get_path_name(),source_sha256=sha,triangles=[],slots=[str(s.material_slot_name) for s in asset.materials])
for lod in range(3):
    output,status=g.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),
                    u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError(f'Glove render LOD {lod} read failed')
    receipt['triangles'].append(output.get_triangle_count())
(R/'saved.json').write_text(json.dumps(receipt,indent=2))
print('TS01_NATIVE_SHOTGUN_GLOVE_SAVED',receipt)
