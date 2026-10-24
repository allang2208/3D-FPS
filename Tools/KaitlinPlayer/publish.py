"""Publish only Kaitlin's owned variant fields after their saved-asset stages."""
import argparse
import copy
import hashlib
import json
import os
import runpy
import tempfile
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/KaitlinPlayer20261023'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
parser = argparse.ArgumentParser()
parser.add_argument('--publish', action='store_true')
args = parser.parse_args()
for stage in ('save_body', 'retarget', 'save_world_garments', 'save_backpacks', 'save_view_skin',
              'capture_death_tracks', 'save_robe_cloth', 'save_skin_patches', 'capture_groom_materials'):
    receipt = read(WORK / (stage + '_status.json'))
    if not receipt['complete']:
        raise RuntimeError('Finish the saved-asset stage before publishing: ' + stage)
body_path = PROJECT / 'Content/ColdSteelData/player_body.json'
modular_path = PROJECT / 'Content/ColdSteelData/modular_outfits.json'
body_before, modular_before = body_path.read_bytes(), modular_path.read_bytes()
current_body = json.loads(body_before.decode('utf-8-sig'))
current_modular = json.loads(modular_before.decode('utf-8-sig'))
source_body = read(WORK / 'FitInputs/player_body.json')
source_modular = read(WORK / 'FitInputs/modular_outfits.json')
world = read(WORK / 'WorldGarments/saved_assets.json')
view_skin = read(WORK / 'ViewSkin/saved_assets.json')
new_body = read(WORK / 'Body/saved_asset.json')['mesh']
native_skin = source_modular['profiles'][source_body['body_mesh']]['native_bare_skin']
replacements = {**world, **view_skin, native_skin: new_body}
retargeted = read(WORK / 'retargeted_assets.json')
missing = [key for key, path in current_body['clips'].items() if path not in retargeted]
if missing:
    raise RuntimeError('New motion sources need their female retarget before publication: ' + ', '.join(missing))


def remap(value):
    if isinstance(value, str):
        return replacements.get(value, 'Kaitlin' if value == 'Jason' else value)
    if isinstance(value, list):
        return [remap(child) for child in value]
    if isinstance(value, dict):
        return {remap(key): remap(child) for key, child in value.items()}
    return value


# Copy non-asset behavior from the current configuration; the complete authored
# outfit source is the captured revision, so later male changes stay untouched.
female = copy.deepcopy({key: value for key, value in current_body.items() if key != 'body_variants'})
female.update(ready=True, body_mesh=new_body, first_person_lower_body_mesh=new_body, default_head='kaitlin')
female['first_person_hidden_materials'] = source_modular['profiles'][source_body['body_mesh']]['owner_body_hidden_materials']
female['clips'] = {key: retargeted[path] for key, path in current_body['clips'].items()}
calibration = read(WORK / 'calibration.json')
for key in ('pose_scale', 'consume_mouth_in_head', 'first_person_body', 'death_presentation'):
    female[key] = calibration[key]
female['outfits'] = read(WORK / 'Backpacks/mounts.json')
female['head_equipment'] = read(WORK / 'Headwear/mounts.json')
if set(current_body['outfits']) - set(female['outfits']):
    raise RuntimeError('New backpacks need their female fit before publication.')
if set(current_body['head_equipment']) - set(female['head_equipment']):
    raise RuntimeError('New headpieces need their female mount before publication.')
# Hair visibility is headwear behavior, not a frozen female fit measurement.
# Keep current policy when reusing previously captured mount transforms.
for key, recipe in female['head_equipment'].items():
    recipe['covers_scalp_hair'] = current_body['head_equipment'][key].get('covers_scalp_hair', False)
grooms = read(WORK / 'groom_recipes.json')
scalp = [dict(row, simulate=True) for row in grooms if '/Hair_' in row['asset']]
details = [row for row in grooms if '/Eyebrows_' in row['asset'] or '/Eyelashes_' in row['asset']]
if len(scalp) != 1 or len(details) != 2:
    raise RuntimeError('The selected native hair, brow and lash recipes must be saved.')
female['heads'] = {'kaitlin': {
    'mesh': '/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Face/SKM_MHC_Kaitlin_FaceMesh.SKM_MHC_Kaitlin_FaceMesh',
    'default_hair': 'long_straight', 'grooms': details,
    'hair_styles': {'long_straight': {'grooms': scalp}, 'bald': {'grooms': []}}}}
variant = copy.deepcopy({key: value for key, value in source_modular.items() if key not in ('body_variants', 'profiles', 'items')})
variant['items'] = remap(source_modular['items'])
variant['native_bare_hands_default'] = True
variant['profiles'] = {}
for path, profile in current_modular['profiles'].items():
    if profile.get('rig_profile') in ('Jason', 'Body'):
        continue
    if profile.get('native_bare_skin') and profile['native_bare_skin'] not in view_skin:
        raise RuntimeError('New weapon profile needs its skin follower: ' + path)
    updated = remap(profile)
    if profile.get('native_bare_skin'):
        updated['base'] = updated['native_bare_skin']
        updated['bare_arms_candidate'] = updated['native_bare_skin']
        updated['native_bare_arms'] = False
    variant['profiles'][path] = updated
world_profile = remap(source_modular['profiles'][source_body['body_mesh']])
world_profile['base'] = world_profile['native_bare_skin'] = new_body
body_materials = read(WORK / 'Body/saved_asset.json')['materials']
world_profile['hide_source_materials'] = list(range(len(body_materials)))
# This is the inherited face/body overlap proxy, which was transparent in the
# male material recipe. Preserve that coverage when all skin slots use UHM.
world_profile['base_hide_materials'] = sorted(set(world_profile.get('base_hide_materials', [])) |
                                              {index for index, material in enumerate(body_materials) if material['slot'] == 'MaskedProxy'})
variant['profiles'][new_body] = world_profile
output = WORK / 'RuntimeRecipes'
output.mkdir(exist_ok=True)
(output / 'player_body_kaitlin.json').write_text(json.dumps(female, ensure_ascii=False, indent=2), encoding='utf-8')
(output / 'modular_outfits_kaitlin.json').write_text(json.dumps(variant, ensure_ascii=False, indent=2), encoding='utf-8')
if args.publish:
    transaction = runpy.run_path(str(PROJECT / 'Tools/PlayerBody/config_transaction.py'))
    commit = transaction['commit']
    # The shared player-body commit intentionally rejects other filenames.
    # Reuse its text-preserving field editor for this one owned modular field.
    modular_text = transaction['_set'](modular_before.decode('utf-8-sig'), ('body_variants', 'kaitlin'), variant)
    modular_bytes = (b'\xef\xbb\xbf' if modular_before.startswith(b'\xef\xbb\xbf') else b'') + modular_text.encode('utf-8')
    with transaction['_lock'](PROJECT / 'Saved/ModularOutfitConfigWrites/writer.lock'):
        if modular_path.read_bytes() != modular_before:
            raise RuntimeError('Modular configuration changed; merge again from the current file.')
        receipt_dir = WORK / 'RuntimeRecipes/Publication'
        receipt_dir.mkdir(exist_ok=True)
        (receipt_dir / 'modular_before.json').write_bytes(modular_before)
        (receipt_dir / 'modular_after.json').write_bytes(modular_bytes)
        with tempfile.NamedTemporaryFile(dir=modular_path.parent, prefix='.kaitlin-outfits-', suffix='.tmp', delete=False) as stream:
            temp_path = Path(stream.name)
            stream.write(modular_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            if modular_path.read_bytes() != modular_before:
                raise RuntimeError('An external writer changed modular configuration; preserving it.')
            os.replace(temp_path, modular_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
    modular_receipt = {'status': 'applied', 'owned_paths': [['body_variants', 'kaitlin']],
                       'before_sha256': hashlib.sha256(modular_before).hexdigest(),
                       'after_sha256': hashlib.sha256(modular_bytes).hexdigest()}
    current_body.setdefault('body_variants', {})['kaitlin'] = female
    body_receipt = commit(body_path, body_before, current_body,
                          owned_paths=[('body_variants', 'kaitlin')], producer=__file__)
    (WORK / 'published.json').write_text(json.dumps({'status': 'local_runtime_variant_published',
        'body': body_receipt, 'modular': modular_receipt, 'runtime_tested': False,
        'body_variant': 'kaitlin', 'world_garments': len(world), 'backpack_variants': len(female['outfits']) * 6,
        'animation_mappings': len(female['clips']), 'active_unique_animations': len(set(female['clips'].values())),
        'headpieces': len(female['head_equipment']), 'view_skin_meshes': len(view_skin)}, indent=2), encoding='utf-8')
    print('KAITLIN_RUNTIME_VARIANT_PUBLISHED', flush=True)
else:
    print('KAITLIN_RUNTIME_RECIPES_PREPARED', flush=True)
