"""Install only missing rune flow and synchronize the stale whirlwind shader."""
import hashlib
import json
import runpy
import shutil
import traceback
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary
before = json.loads((ROOT / 'material-state.json').read_text(encoding='utf-8'))
SOURCE = '/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2.M_SilverRuneSurfaceV2'
TEMPORAL = '/Game/Skills/Whirlwind20260920/ForegroundV3/M_SilverRuneSurfaceV2_478649ff_WhirlwindV3.M_SilverRuneSurfaceV2_478649ff_WhirlwindV3'
knives = {p: (8., 28.135 if 'Hunter' in p else 18.29) for p in before['materials'] if '/M_KukriMark_' in p}
targets = list(knives) + [TEMPORAL]
receipt = {'complete': False, 'saved_assets': [], 'compile_results': {}, 'runtime_tested': False,
           'preserved_existing_dynamic_materials': [p for p in before['materials'] if p not in targets]}

def record():
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

def custom_code(mat):
    return {n.get_name(): n.get_editor_property('code') for n in L.get_material_expressions(mat)
            if isinstance(n, u.MaterialExpressionCustom)}

def install():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor(): raise RuntimeError('PIE active; no material changes made')
    packages = {p.split('.')[0] for p in targets}
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty & packages: raise RuntimeError('Unsaved target materials preserved: ' + ', '.join(sorted(dirty & packages)))
    loaded = {p: u.load_asset(p) for p in targets + [SOURCE]}
    for path, obj in loaded.items():
        if not obj: raise RuntimeError('Missing material: ' + path)
        expected = {n['name']: n['code'] for n in before['materials'][path]['nodes'] if 'code' in n}
        if custom_code(obj) != expected: raise RuntimeError('Material changed since read; preserve: ' + path)
    for path in targets:
        relative = path.split('.')[0].removeprefix('/Game/') + '.uasset'
        dst = ROOT / 'Before/Content' / relative
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJECT / 'Content' / relative, dst)

    add_flow = runpy.run_path(str(ROOT / 'knife_material.py'))['add_knife_flow']
    for path, (start, length) in knives.items(): add_flow(loaded[path], start, length)

    source, dest = loaded[SOURCE], loaded[TEMPORAL]
    source_nodes = list(L.get_material_expressions(source))
    dest_nodes = list(L.get_material_expressions(dest))
    src = next(n for n in source_nodes if isinstance(n, u.MaterialExpressionCustom) and 'RuneTexture' in L.get_material_expression_input_names(n))
    dst = next(n for n in dest_nodes if isinstance(n, u.MaterialExpressionCustom) and 'RuneTexture' in L.get_material_expression_input_names(n))
    # Keep the temporal material's vertex/depth graph and all existing input wires.
    pins = list(dst.get_editor_property('inputs'))
    existing = {str(p.get_editor_property('input_name')) for p in pins}
    scalar_vector = (u.MaterialExpressionScalarParameter, u.MaterialExpressionVectorParameter)
    src_params = {str(n.get_editor_property('parameter_name')): n for n in source_nodes if isinstance(n, scalar_vector)}
    dst_params = {str(n.get_editor_property('parameter_name')): n for n in dest_nodes if isinstance(n, scalar_vector)}
    for name in L.get_material_expression_input_names(src):
        if name not in src_params: continue
        n = dst_params.get(name)
        if not n:
            cls = u.MaterialExpressionScalarParameter if isinstance(src_params[name], u.MaterialExpressionScalarParameter) else u.MaterialExpressionVectorParameter
            n = L.create_material_expression(dest, cls, -1200, 1100)
            n.set_editor_property('parameter_name', name); dst_params[name] = n
        n.set_editor_property('default_value', src_params[name].get_editor_property('default_value'))
        if name not in existing:
            pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    dst.set_editor_property('inputs', pins)
    for name in L.get_material_expression_input_names(src):
        if name in dst_params and name not in existing:
            if not L.connect_material_expressions(dst_params[name], '', dst, name): raise RuntimeError('Cannot wire ' + name)
    dst.set_editor_property('code', src.get_editor_property('code'))

    for path in targets:
        obj = loaded[path]
        errors = list(L.recompile_material(obj) or [])
        receipt['compile_results'][path] = [str(e) for e in errors]; record()
        if errors: raise RuntimeError('Material compile errors: ' + path)
        if not E.save_loaded_asset(obj, False): raise RuntimeError('Material save failed: ' + path)
        receipt['saved_assets'].append(path); record()
    receipt['complete'] = True
    record()
    print('ALL_WEAPON_RUNE_FLOW_SAVED materials=' + str(len(targets)) + ' knife_combinations=18 runtime_tested=false')

try: install()
except Exception:
    receipt['error'] = traceback.format_exc(); record(); raise
