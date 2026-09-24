"""Reimport only the corrected atlas, then read its empty-frame alpha on GPU."""
import importlib
import json
from pathlib import Path
import sys
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if root!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
source=root/'SourceAssets/RiverSplashNatural20260924'
sys.path.insert(0,str(root/'Tools/Fluids'))
import author_river_splash_natural as natural
natural=importlib.reload(natural)
natural.b.SAVED.clear()
texture=natural.texture()
u.EditorAssetLibrary.set_metadata_tag(texture,'RiverSplash.EmptyFrameFix','1')
natural.b.save(texture)
natural.material('M_RiverCrown',True,texture)
diagnosis=source/'CardFix/diagnose_gpu_alpha.py'
exec(compile(diagnosis.read_text(encoding='utf-8'),str(diagnosis),'exec'),
     {'__file__':str(diagnosis),'REPORT_FILENAME':'gpu-alpha-after.json','REQUIRE_EMPTY_FRAMES':True})
manifest=json.loads((source/'bake-manifest.json').read_text(encoding='utf-8'))
report={'saved':list(dict.fromkeys(natural.b.SAVED)),
        'root_cause':'Empty cached liquid mesh fell back to the Mantaflow domain cube in the bake',
        'transparent_frames':manifest['empty_frames'],
        'preserved_nonempty_exrs':True,'resimulated':False,
        'gpu_empty_frame_alpha_checked':True,'gameplay_tested':False,
        'resident_texture_budget_bytes':2796208,'extra_samples':0,'extra_particles':0}
(source/'CardFix/empty-frame-fix-delivery.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('RIVER_EMPTY_FRAME_FIX_SAVED '+json.dumps(report))
