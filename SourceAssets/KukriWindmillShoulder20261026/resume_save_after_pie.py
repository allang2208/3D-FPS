"""Resume the V13 start package this task authored while PIE blocked its save."""
import json
import runpy
from pathlib import Path
import unreal as u

out=Path(__file__).resolve().parent
receipt=json.loads((out/'assets-saved.json').read_text())
asset=receipt['bodies']['jason']['clips']['Kukri.FullBody.Whirlwind.Start']
if '/WhirlwindWindmillV13/A_Kukri_Whirlwind_Start_WindmillShoulder.' not in asset:
    raise RuntimeError('The interrupted package is outside this task')
clip=u.load_asset(asset)
if clip:
    owner=u.EditorAssetLibrary.get_metadata_tag(clip,'AuthoringScript')
    if owner not in ('','SourceAssets/KukriWindmillShoulder20261026/author.py'):
        raise RuntimeError('The interrupted package has another author')
    u.EditorAssetLibrary.set_metadata_tag(clip,'AuthoringScript','SourceAssets/KukriWindmillShoulder20261026/author.py')
runpy.run_path(str(out/'save_all.py'))
