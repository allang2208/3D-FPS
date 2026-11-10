"""Create the elemental arrow's fitted warm charge flame; author/save only."""
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
SOURCE = '/Game/Skills/FlameArmor20261108/AllWeaponsV12/NS_FlameArmorWeapon'
DEST = '/Game/Skills/ElementalArrow20261109/WarmFireV2/NS_ElementalArrowFire'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import emitters, ref, setdata, put

if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before creating and saving the elemental arrow warm flame')
dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if SOURCE in dirty or DEST in dirty:
    raise RuntimeError('Preserve unsaved source/target flame assets')
asset_file = ROOT / ('Content/' + DEST.removeprefix('/Game/') + '.uasset')
backup = OUT / 'Before/NS_ElementalArrowFire.uasset'
if asset_file.exists() and not backup.exists():
    shutil.copy2(asset_file, backup)
u.EditorAssetLibrary.make_directory(DEST.rsplit('/', 1)[0])
system = u.load_asset(DEST) if u.EditorAssetLibrary.does_asset_exist(DEST) else u.EditorAssetLibrary.duplicate_asset(SOURCE, DEST)
if system is None:
    raise RuntimeError('Cannot copy the restored warm weapon flame')

# Preserve its four native layers and warm materials, including the saved
# nonnegative random fields and exposure tuning. All roots stay in arrow space.
system.set_editor_property('require_current_frame_data', True)
system.set_editor_property('fixed_tick_delta', False)
layers = emitters(system)
for name in layers:
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
            {'bLocalSpace': True, 'bInterpolatedSpawning': False})
# Preparation has no 30-second buff limit. Keep the existing fixed core cohort
# alive until the owning visual is cleared, instead of periodic respawn flashes.
put(system, 'WeaponFireballCore', 'ParticleUpdateScript', 'ParticleState',
    'Kill Particles When Lifetime Has Elapsed', '(Value=0)', '/Script/Niagara.NiagaraBool')
u.EditorAssetLibrary.set_metadata_tag(system, 'ElementalArrow.WarmFireRevision', '20261109-v2')
u.EditorAssetLibrary.set_metadata_tag(system, 'ElementalArrow.WarmFireSource', SOURCE)
if not u.RainAssetEditor.compile_rain(system, True):
    raise RuntimeError('Elemental arrow Niagara compilation failed')
if not u.EditorAssetLibrary.save_loaded_asset(system, False):
    raise RuntimeError('Elemental arrow warm flame save failed')
receipt = dict(asset=system.get_path_name(), source=SOURCE, saved=True, emitters=layers,
               persistent_core=True, runtime_tested=False, editor_started=False)
(OUT / 'saved-asset.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('ELEMENTAL_ARROW_WARM_FIRE_SAVED ' + json.dumps(receipt))
