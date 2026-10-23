"""Save only the new mountain/knit variant. Existing meshes/materials are read-only."""
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME'); R=P/'SourceAssets/BackpackMotion20261022'
spec=importlib.util.spec_from_file_location('backpack_motion_save',P/'Tools/BackpackMotion/save_assets.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
row=next(r for r in m.plan['variants'] if r['kind']=='mountain' and r['profile']=='knit_sweater')
path=row['asset'].split('.')[0]
if not path.startswith('/Game/Characters/BackpackMotion20261022/MountainR2/'):
    raise RuntimeError('Refit writer only owns the new MountainR2 package')
digest=hashlib.sha256(Path(row['source']).read_bytes()+Path(row['mask']).read_bytes()).hexdigest()
source=u.load_asset(row['input_asset'])
if not source:raise RuntimeError('Missing accepted mountain source')
if any(p.get_path_name()==path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Refit package has unsaved edits')
mesh=u.load_asset(path) or m.E.duplicate_asset(row['input_asset'].split('.')[0],path)
mask=json.loads(Path(row['mask']).read_text());counts=[]
for lod in range(m.S.get_lod_count(source)):
    dm,status=m.G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_index=lod))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read retained LOD')
    m.apply_fit_delta(dm,row['fit_delta']);m.apply_mask(dm,mask)
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=m.G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD(lod_index=lod))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save fitted LOD')
    counts.append(dm.get_triangle_count());del dm;gc.collect()
m.E.set_metadata_tag(mesh,'BackpackMotionRefitRevision','MountainKnitR2_20261022')
m.save(mesh)
m.saved['variants']['mountain/knit_sweater']={'asset':mesh.get_path_name(),'sha256':digest,'saved':True,
    'lod_triangles':counts,'materials':[slot.material_interface.get_path_name() for slot in mesh.materials],
    'fit_delta':row['fit_delta'],'previous_asset':row['input_asset']}
m.receipt()
print('BACKPACK_REFIT_SAVED',mesh.get_path_name(),counts,flush=True)
