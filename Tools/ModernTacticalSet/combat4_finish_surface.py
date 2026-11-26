"""Finalize panel normals, propagate native variants and regenerate their actual artwork."""
import runpy,gc,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR4'
receipt=R/'artwork-saved.json';data=json.loads(receipt.read_text());data['completed']=False;receipt.write_text(json.dumps(data,indent=2))
(R/'surface-finalized.json').write_text(json.dumps(dict(completed=False)))
for name in ['combat4_details.py','combat4_assemble.py','combat4_fit_collar.py','combat4_sources.py']:
    print('R4_SURFACE_STAGE',name,flush=True);runpy.run_path(str(P/'Tools/ModernTacticalSet'/name),run_name='__main__');gc.collect()
(R/'surface-finalized.json').write_text(json.dumps(dict(completed=True,sewn_panel_normals='Area weighted smooth outer facing; turned edge retains its split normal',all_native_variants_produced=True,artwork_requires_save=True),indent=2))
print('R4_FINAL_SURFACES_AND_ARTWORK_AUTHORED',flush=True)
