"""Save a dedicated copy of the existing bound local lightning ribbons."""
import json
import shutil
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
SOURCE='/Game/Weapons/ElectrifiedMelee/NS_ElectrifiedBlade'
DEST='/Game/Skills/LightningHaste20261019/NS_LightningHasteArc'
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if DEST in dirty:raise RuntimeError('Preserve unsaved Lightning Haste asset')
u.EditorAssetLibrary.make_directory(DEST.rsplit('/',1)[0])
system=u.load_asset(DEST) if u.EditorAssetLibrary.does_asset_exist(DEST) else u.EditorAssetLibrary.duplicate_asset(SOURCE,DEST)
if not system:raise RuntimeError('Missing bound lightning ribbon source '+SOURCE)
# The copied melee effect is a single burst with 0.24s particles. Haste needs a
# fixed ribbon cohort for the whole buff; its component owns fade and destruction.
backup=ROOT/'SourceAssets/LightningHasteVFX20261107/Before/NS_LightningHasteArc.uasset'
asset_file=ROOT/'Content/Skills/LightningHaste20261019/NS_LightningHasteArc.uasset'
if asset_file.exists() and not backup.exists():
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(asset_file,backup)
for emitter in ('Currency','MainPower'):
    if not u.RainAssetEditor.set_input(system,emitter,'ParticleUpdateScript','ParticleState',
                                      'Kill Particles When Lifetime Has Elapsed','/Script/Niagara.NiagaraBool','(Value=0)'):
        raise RuntimeError('Cannot author persistent haste ribbon: '+emitter)
system.set_editor_property('require_current_frame_data',True)
# Compilation recreates the spline interfaces; restore their explicit user binding afterwards.
if not u.RainAssetEditor.bind_spline_user_object(system,'User.BladeSpline'):
    raise RuntimeError('Lightning Haste spline compilation/binding failed')
u.EditorAssetLibrary.set_metadata_tag(system,'LightningHaste.Source',SOURCE)
u.EditorAssetLibrary.set_metadata_tag(system,'LightningHaste.Revision','FourLimbV2_PersistentCohort_20261125')
if not u.EditorAssetLibrary.save_loaded_asset(system,False):raise RuntimeError('Lightning Haste asset was not saved')
out=ROOT/'SourceAssets/LightningHasteVFX20261107';out.mkdir(parents=True,exist_ok=True)
receipt={'saved_assets':[system.get_path_name()],'source':SOURCE,'spline_parameter':'User.BladeSpline',
         'active_components_per_player':4,'dynamic_lights':0,'particle_lifetime_owner':'haste component',
         'repeating_spawns':False,'gameplay_tested':False,'rendered':False}
(out/'asset-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
