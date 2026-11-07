"""Update the five active broadblade-only materials in place."""
from pathlib import Path
import ast
import json
import shutil
import sys
import unreal as u

P = Path('D:/FPS3D/FPSGAME/SourceAssets/HighlandBroadbladeGuardFinish20261106')
ROOT = P.parents[1]
sys.path.insert(0, str(P))
from seat_finish import REVISION, native_protection, bind_gale_seat

L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
previous = P / 'install.py'
functions = ast.parse(previous.read_text(encoding='utf-8')).body
helpers = [node for node in functions if isinstance(node, ast.FunctionDef)
           and node.name in {'wire', 'root', 'input_of'}]
exec(compile(ast.Module(body=helpers, type_ignores=[]), str(previous), 'exec'))

gale_folder = '/Game/Weapons/HighlandClaymore20260922/GaleWing20261107/Materials/'
paths = json.loads((P/'saved-assets.json').read_text(encoding='utf-8'))['materials']
paths += [gale_folder + 'M_GaleWing_Broadblade_' + slot for slot in ('Steel', 'Polish')]
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None:
    raise RuntimeError('Preserving active PIE')

targets = []
for path in paths:
    package = path.partition('.')[0]
    if package in dirty:
        raise RuntimeError('Preserving unsaved edits to ' + package)
    mat = u.load_asset(package)
    if not mat:
        raise RuntimeError('Missing material ' + package)
    targets.append((package, mat))

receipt = []
for package, mat in targets:
    if E.get_metadata_tag(mat, 'HighlandSeatFinish') != REVISION:
        relative = package.removeprefix('/Game/') + '.uasset'
        backup = ROOT / 'Saved/HighlandBroadbladeSeat20261107/Before' / relative
        if not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / 'Content' / relative, backup)
        if package.startswith(gale_folder):
            properties = ('BASE_COLOR', 'NORMAL', 'ROUGHNESS', 'METALLIC', 'ANISOTROPY', 'TANGENT')
            fields = {name: root(mat, name)[0] for name in properties}
            if not all(isinstance(expr, u.MaterialExpressionCustom) for expr in fields.values()):
                raise RuntimeError('Unexpected Gale Wing finish graph in ' + package)
            bind_gale_seat(mat, fields, wire, root, input_of)
        else:
            masks = [n for n in L.get_material_expressions(mat) if isinstance(n, u.MaterialExpressionCustom)
                     and str(n.get_editor_property('desc')) == 'BroadbladeGuardFinish20261106R1 gem and bezel preservation']
            if len(masks) != 1:
                raise RuntimeError('Missing existing guard preservation mask in ' + package)
            masks[0].set_editor_property('code', native_protection(mat))
        errors = L.recompile_material(mat)
        if errors:
            raise RuntimeError('Material compilation failed: ' + str(errors))
        E.set_metadata_tag(mat, 'HighlandSeatFinish', REVISION)
        if not E.save_loaded_asset(mat, False):
            raise RuntimeError('Could not save ' + package)
    receipt.append(mat.get_path_name())

(P/'saved-seat-boundary.json').write_text(json.dumps(
    {'revision': REVISION, 'materials': receipt, 'runtime_tested': False},
    ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('BROADBLADE_SEAT_BOUNDARY_SAVED ' + str(len(receipt)))
