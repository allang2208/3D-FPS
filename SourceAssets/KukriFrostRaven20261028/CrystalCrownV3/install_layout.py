"""Compile and save only the crystal crown's lower-throat width fit."""
import hashlib
import json
from pathlib import Path

import unreal as u

P = Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriFrostRaven20261028/CrystalCrownV3/install_layout.py').resolve().parent
HUD = '/Game/Weapons/Kukri20261020/FrostRaven20261028/M_FrostRavenEnergyHud'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('End PIE before saving the crown width adjustment')
dirty = {str(package.get_path_name()) for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if HUD in dirty:
    raise RuntimeError('Preserve unsaved frost HUD changes')
hud = u.load_asset(HUD)
if not hud:
    raise RuntimeError('Missing frost HUD material')
custom = next(node for node in L.get_material_expressions(hud) if isinstance(node, u.MaterialExpressionCustom))
code = (P / 'FrostRavenCrystalHud.hlsl').read_text('utf-8')
receipt = {'complete': False, 'material_compiled': False, 'saved_assets': [], 'runtime_tested': False,
           'hlsl_sha256': hashlib.sha256(code.encode()).hexdigest(),
           'layout': json.loads((P / 'crown-layout.json').read_text('utf-8')),
           'design': 'Lower throat matches column width; upper eagle silhouette and viewport placement preserved'}


def record():
    (P / 'width-fit-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


record()
custom.set_editor_properties({'code': code, 'description': 'FrostRavenUnifiedCrystalCrownV3_WidthFit'})
E.set_metadata_tag(hud, 'CrownJoin', 'IntegralCrystalRoot_WidthMatchedV1')
errors = L.recompile_material(hud)
if errors:
    raise RuntimeError('HUD material compilation failed: ' + str(errors))
if not u.PoisonMaggotMonster.compile_material_assets([hud]):
    raise RuntimeError('HUD material compilation failed')
receipt['material_compiled'] = True
record()
if not E.save_loaded_asset(hud, False):
    raise RuntimeError('Cannot save the frost HUD width adjustment')
receipt['saved_assets'].append(hud.get_path_name())
receipt['complete'] = True
record()
u.log('FROST_RAVEN_CRYSTAL_WIDTH_FIT_SAVED')
