"""Author the approved softer torch and muzzle presentation. No runtime tests.

Run after the original torch / gunplay builders. Only the two project-owned
Niagara systems and two dedicated torch material instances are saved.
"""
from pathlib import Path
import json
import shutil
import unreal

ROOT = Path(unreal.Paths.project_dir())
BACKUP = ROOT / 'Saved/LightingSoft20260919/Before'
BACKUP.mkdir(parents=True, exist_ok=True)
API = unreal.get_default_object(unreal.NiagaraToolset_System)
LIB = unreal.MaterialEditingLibrary
TORCH = '/Game/Props/RomanColumn20260915/NS_TorchFlame'
MUZZLE = '/Game/Weapons/GunplayFX/NS_FPS_MuzzleFlashV10'


def backup(path):
    source = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    target = BACKUP / source.name
    if not target.exists():
        shutil.copy2(source, target)


def save(asset):
    # Save exactly this package; never flush other sessions' dirty content/maps.
    if not unreal.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    print('SOFT_FIRE_SAVED', asset.get_path_name())


def renderer_ref(system, emitter):
    result = unreal.NiagaraExt_StackItemReference()
    for key, value in dict(system=system, emitter_name=emitter, renderer_index=0).items():
        result.set_editor_property(key, value)
    return result


for path in [TORCH, MUZZLE]:
    backup(path)

torch = unreal.load_asset(TORCH)
for number, energy in [(1, 12.0), (2, 24.0)]:
    source = '/Game/Vefects/Free_Fire/Shared/Materials/MI_VFX_Fire_%02d' % number
    destination = '/Game/Props/RomanColumn20260915/MI_TorchSoft_Flame%02d' % number
    material = (unreal.load_asset(destination) if unreal.EditorAssetLibrary.does_asset_exist(destination)
                else unreal.EditorAssetLibrary.duplicate_asset(source, destination))
    LIB.set_material_instance_scalar_parameter_value(material, 'Emissive_Intensity', energy)
    LIB.update_material_instance(material)
    save(material)
    data = unreal.NiagaraExt_RendererData()
    data.set_editor_property('property_values', json.dumps({'Material': material.get_path_name()}))
    API.call_method('SetRendererData', (renderer_ref(torch, 'NE_Flame_%02d' % number), data))

if not unreal.RainAssetEditor.compile_rain(torch):
    raise RuntimeError('Torch asset compilation failed')
save(torch)

muzzle = unreal.load_asset(MUZZLE)
for emitter, low, high in [('Flash_Center', .025, .040),
                          ('MuzzleFlash_Front', .040, .060),
                          ('MuzzleFlash_Side', .035, .055)]:
    for name, value in [('Lifetime Min', low), ('Lifetime Max', high)]:
        if not unreal.RainAssetEditor.set_input(muzzle, emitter, 'ParticleSpawnScript',
                'InitializeParticle', name, '/Script/Niagara.NiagaraFloat', '(Value=%s)' % value):
            raise RuntimeError('Could not author ' + emitter + '/' + name)
if not unreal.RainAssetEditor.compile_rain(muzzle):
    raise RuntimeError('Muzzle asset compilation failed')
save(muzzle)
print('SOFT_FIRE_AUTHORING_COMPLETE')
