"""Resume this task's loop package after the unsupported-rate import stopped."""
import json
import runpy
from pathlib import Path
import unreal as u

out=Path(__file__).resolve().parent
folder='/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/Jason/Animations/WhirlwindWindmillV12'
name='A_Kukri_Whirlwind_Loop_WindmillReverse'
asset=folder+'/'+name+'.'+name
disk=out.parents[1]/'Content'/folder.removeprefix('/Game/')/(name+'.uasset')
clip=u.load_asset(asset)
if clip:
    # The failed save-result.json identifies this exact newly created package.
    if asset.split('.')[0] not in (out/'save-after-pie-result.json').read_text():
        raise RuntimeError('Failed creation receipt does not identify this package')
    owner=u.EditorAssetLibrary.get_metadata_tag(clip,'AuthoringScript')
    if owner not in ('','SourceAssets/KukriWindmillReverse20261026/author.py'):
        raise RuntimeError('The interrupted package has another author')
    u.EditorAssetLibrary.set_metadata_tag(clip,'AuthoringScript','SourceAssets/KukriWindmillReverse20261026/author.py')
    receipt=json.loads((out/'assets-saved.json').read_text())
    receipt['bodies']['jason']['clips']['Kukri.FullBody.Whirlwind.Loop']=asset
    (out/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
runpy.run_path(str(out/'save_all.py'))
