"""Read local candidate mesh dimensions and material/particle dependencies; no rendering."""
import json
from pathlib import Path
import unreal as u

paths = ['/Game/NiagaraExamples/StaticMesh/SM_SimpleProjectile'] + [
    '/Game/NiagaraExamples/StaticMesh/SM_GlassShard_0'+str(n) for n in range(1,4)]
rows=[]
for path in paths:
    mesh=u.load_asset(path)
    if not mesh: continue
    bounds=mesh.get_bounds()
    rows.append({'path':path,'extent':str(bounds.box_extent),'origin':str(bounds.origin),
                 'materials':[str(m.material_interface) for m in mesh.static_materials]})
for path in ['/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Hit/P_Ice',
             '/Game/_SplineVFX/NS/NS_Spline_Frost']:
    asset=u.load_asset(path)
    rows.append({'path':path,'class':asset.get_class().get_name() if asset else None})
out=Path(u.Paths.project_saved_dir())/'IceSpikeSourceInventory.json'
out.write_text(json.dumps(rows,indent=2),encoding='utf-8')
u.log('ICE_SOURCE_INVENTORY '+str(out))
