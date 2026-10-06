"""Rebuild capri wearing/display meshes while reusing existing materials."""
import importlib.util,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SmokeGreyCapri20261004'
spec=importlib.util.spec_from_file_location('capri_crotch_repair',str(P/'Tools/SmokeGreyCapri/save_assets.py'))
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)
pipeline.main(reuse_materials=True)
saved=json.loads((R/'saved_assets.json').read_text())
(R/'crotch-repair-saved-20261005.json').write_text(json.dumps(dict(revision='CrotchSeamFix20261005',assets=saved,geometry='continuous welded waist, seat and legs',binding='bilateral centre seam with 6cm transition into each thigh',materials_reused=True,config_paths_unchanged=True,runtime_tested=False),indent=2),encoding='utf-8')
print('CAPRI_CROTCH_REPAIR_SAVED',flush=True)
