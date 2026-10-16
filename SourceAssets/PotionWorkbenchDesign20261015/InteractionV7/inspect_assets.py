"""Requested offline asset check: dimensions, assigned materials and saved packages only."""
import json,unreal as u
from pathlib import Path
R=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=(R/'UEImportHost').resolve():raise RuntimeError('Wrong project')
manifest=json.loads((R/'asset-manifest.json').read_text('utf8'));out=[]
for spec in manifest['meshes']:
    path='/Game/Building/PotionWorkbench20261015/InteractionV7/'+spec['name']
    mesh=u.load_asset(path)
    if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Missing '+path)
    box=mesh.get_bounding_box();low=[box.min.x,box.min.y,box.min.z];high=[box.max.x,box.max.y,box.max.z]
    error=max(abs(a-b) for v,w in zip([low,high],spec['bounds_ue_cm']) for a,b in zip(v,w))
    if error>.02:raise RuntimeError('FBX dimensions differ '+spec['name']+' '+str(error))
    materials=[x.material_interface.get_path_name() if x.material_interface else '' for x in mesh.static_materials]
    if any(not p for p in materials):raise RuntimeError('Unassigned material '+path)
    out.append(dict(asset=path,bounds=[low,high],max_export_error_cm=error,materials=materials))
(R/'asset-check.json').write_text(json.dumps(dict(meshes=out,rendered=False,runtime_tested=False),indent=2),'utf8')
u.log('ALCHEMY_V7_STATIC_ASSET_CHECK_COMPLETE')
