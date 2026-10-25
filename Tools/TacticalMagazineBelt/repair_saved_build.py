"""Persist the corrected build data of this task's female belt only."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/TacticalMagazineBelt20261024';saved=json.loads((R/'saved_assets.json').read_text(encoding='utf-8-sig'))
path=saved['wear']['Kaitlin']['asset'];asset=u.load_asset(path)
if not asset:raise RuntimeError('Missing fitted female belt')
counts=[]
for lod in range(3):
    mesh,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Render LOD did not finish')
    counts.append(mesh.get_triangle_count())
asset.modify();u.EditorAssetLibrary.set_metadata_tag(asset,'BeltBuildSaveRevision','20261024-render-data-complete')
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Could not save completed female belt build')
report=dict(completed=True,asset=path,render_lod_triangles=counts,geometry_changed=False,materials_changed=False)
(R/'Review20261024/build-cache-repair.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('BELT_BUILD_CACHE_REPAIRED',path,counts,flush=True)
