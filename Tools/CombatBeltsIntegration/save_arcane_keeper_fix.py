"""Save an isolated revision; the old loaded wear mesh is preserved."""
import sys
import gc,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import save_assets as assets
assets.require_asset_window()
assets.R=assets.P/'SourceAssets/ArcaneConduitBelt20261025/KeeperFixR2'
assets.destination=lambda row:'/Game/Characters/ModularOutfit20260924/ArcaneConduitBelt20261025/KeeperFixR2'
assets.produce('arcane')

# Existing saved item instances can retain their original pickup asset path.
# Update that owned compatibility mesh as well, retaining its prior package.
out=assets.R/'arcane';receipt=assets.read(out/'saved_assets.json')
delivery=assets.read(out/'delivery.json')
rows=next(v['lods'] for v in delivery['records'] if v['body']=='Jason')
old_root='/Game/Characters/ModularOutfit20260924/ArcaneConduitBelt20261025/IntegrationR1'
old_path=old_root+'/Pickups/SM_ArcaneConduitBelt'
package=assets.P/'Content'/(old_path.removeprefix('/Game/')+'.uasset')
backup=assets.R/'Before'/package.name;backup.parent.mkdir(parents=True,exist_ok=True)
for original in (package,package.with_suffix('.uexp'),package.with_suffix('.ubulk')):
    target=backup.with_suffix(original.suffix)
    if original.exists() and not target.exists():shutil.copy2(original,target)
data=assets.read(rows[0]['file'])
offset=[-(min(p[i] for p in data['positions'])+max(p[i] for p in data['positions']))*.5 for i in range(3)]
del data
assets.DEST=old_root
compat=assets.static(rows,old_path,offset)

# The user requested a scoped investigation: read every saved render LOD back.
Q=assets.u.GeometryScript_MeshQueries;L=assets.u.GeometryScript_List
checks=[]
for body,record in receipt['wear'].items():
    mesh=assets.load(record['asset'])
    for lod in range(3):
        dm,status=assets.G.copy_mesh_from_skeletal_mesh(mesh,assets.u.DynamicMesh(),assets.u.GeometryScriptCopyMeshFromAssetOptions(),
            assets.u.GeometryScriptMeshReadLOD(lod_type=assets.u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
        if status!=assets.u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved arcane LOD')
        _,points,_=Q.get_all_vertex_positions(dm,False);points=L.convert_vector_list_to_array(points)
        low=min(p.z for p in points);high=max(p.z for p in points)
        if low<70 or high>125:raise RuntimeError('Saved waist mesh still has a displaced component')
        checks.append(dict(body=body,lod=lod,vertices=len(points),z_cm=[low,high],passed=True))
        del points,dm;gc.collect()
    del mesh
    assets.u.SystemLibrary.collect_garbage()
assets.write(assets.R/'saved-geometry-checks.json',dict(completed=True,render_lods=checks,compatibility_pickup=compat,
    runtime_tested=False,multiplayer_tested=False))
print('ARCANE_KEEPER_FIX_SAVED_AND_READ_BACK',flush=True)
