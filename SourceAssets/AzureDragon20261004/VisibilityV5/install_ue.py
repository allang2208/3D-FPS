"""Patch/save the one retained shared claw material without reimporting the claw, rig or energy geometry."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent
DEST = '/Game/Weapons/AzureDragon20261004'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
receipt = {'complete': False, 'revision': 5, 'saved_assets': [],
           'runtime_tested': False, 'rendered': False}


def record():
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def owned(path, tag, revision):
    if any(str(p.get_name()) == path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved target ' + path)
    asset = u.load_asset(path)
    if not asset or E.get_metadata_tag(asset, tag) != revision:
        raise RuntimeError('Required owned material unavailable: ' + path)
    return asset


def save(mat):
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compilation failed: ' + str(errors))
    E.set_metadata_tag(mat, 'AzureDragonVisibilityRevision', '5')
    if not E.save_loaded_asset(mat, False):
        raise RuntimeError('Cannot save ' + mat.get_path_name())
    receipt['saved_assets'].append(mat.get_path_name())
    record()


record()
mat = owned(DEST + '/Materials/M_AzureDragonClaw', 'AzureDragonRevision', '1')
expressions = list(L.get_material_expressions(mat))
alpha = [x for x in expressions if isinstance(x, u.MaterialExpressionComponentMask)
         and x.get_editor_property('a') and not any(x.get_editor_property(c) for c in ('r', 'g', 'b'))]
if len(alpha) != 1:
    raise RuntimeError('Expected the owned claw alpha node')
mat.set_editor_property('disable_depth_test', True)
mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_AFTER_DOF)
if not L.connect_material_property(alpha[0], '', u.MaterialProperty.MP_OPACITY):
    raise RuntimeError('Cannot connect foreground claw opacity')
for expression in expressions:
    if isinstance(expression, u.MaterialExpressionDepthFade):
        L.delete_material_expression(mat, expression)
save(mat)
receipt['complete'] = True
record()
print('AZURE_DRAGON_VISIBILITY_V5_SAVED materials=1 runtime_tested=false rendered=false')
