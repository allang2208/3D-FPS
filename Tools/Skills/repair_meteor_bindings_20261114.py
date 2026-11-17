"""Complete the requested impact diagnosis by repairing stale template bindings."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from meteor_renderer_bindings import bind_impact_attributes,binding_receipt
OUT=ROOT/'SourceAssets/MeteorVisibilityRepair20261114'
path='/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7/NS_MeteorPressureV7'
if path in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserve unsaved meteor system')
system=u.load_asset(path)
bind_impact_attributes(system)
author=u.DragonBreathAuthorLibrary if hasattr(u,'DragonBreathAuthorLibrary') else u.RainAssetEditor
if not author.compile_rain(system,True):raise RuntimeError('Meteor binding compilation failed')
rows=binding_receipt(system)
if not u.EditorAssetLibrary.save_loaded_asset(system,False):raise RuntimeError('Meteor binding save failed')
(OUT/'binding-repair-receipt.json').write_text(json.dumps(dict(complete=True,system=system.get_path_name(),bindings=rows,runtime_tested=False),indent=2),encoding='utf8')
print('METEOR_BINDINGS_SAVED '+system.get_path_name(),flush=True)
