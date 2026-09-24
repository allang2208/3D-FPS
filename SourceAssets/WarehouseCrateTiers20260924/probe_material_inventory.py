"""Inventory for the surface-material improvement plan (READ-ONLY, fresh process).

Dumps: M_Crate_* graph stats (params, textures + sizes, blend/shading/two-sided, usage flags),
MI_Ritual_* source-chest instances (parent + override params), and every crate texture's
import settings (size, compression, sRGB, mips). Writes probes/material_inventory.json.
"""
import json
import unreal as u

MAT_DIR = '/Game/Props/WarehouseCrateTiers20260924/Materials/'
CRATE_MATS = ['M_Crate_Wood', 'M_Crate_WoodDark', 'M_Crate_Stone', 'M_Crate_Iron',
              'M_Crate_IronDark', 'M_Crate_Gold', 'M_Crate_Silver', 'M_Crate_Gem']
RITUAL_DIR = '/Game/ColdSteelUI/Warehouse20260909/RitualV8/Surfaces/'
RITUAL_MATS = ['MI_Ritual_Frame', 'MI_Ritual_Strap', 'MI_Ritual_Hardware', 'MI_Ritual_Sapphire',
               'MI_Ritual_Champagne', 'MI_Ritual_Engraving']
RUNTIME_DIR = '/Game/ColdSteelUI/Warehouse20260909/RuntimeSurfaces/'
RUNTIME_MATS = ['Surface_Interior_Magic_Blue', 'Surface_Navy_Velvet']
MARBLE = '/Game/ColdSteelUI/Warehouse20260909/ZiaratWhiteMarble/MI_Chest_Ziarat_4K'

out = {'crate_materials': {}, 'ritual_materials': {}, 'textures': {}}

def tex_info(tex):
    if tex is None:
        return None
    key = tex.get_path_name()
    if key not in out['textures']:
        try:
            sz = tex.get_editor_property('size_x'), tex.get_editor_property('size_y')
        except Exception:
            sz = None
        rec = {'size': list(sz) if sz else None}
        try:
            rec['compression'] = str(tex.get_editor_property('compression_settings'))
        except Exception:
            pass
        try:
            rec['srgb'] = bool(tex.get_editor_property('srgb'))
        except Exception:
            pass
        try:
            rec['mips'] = bool(tex.get_editor_property('using_legacy_mipgeneration')) or True
        except Exception:
            pass
        try:
            rec['lod_group'] = str(tex.get_editor_property('lod_group'))
        except Exception:
            pass
        out['textures'][key] = rec
    return key

def walk(mat):
    """Summarize material expression graph."""
    kinds = {}
    textures = []
    params = {'scalar': [], 'vector': [], 'texture': [], 'switch': []}
    try:
        exprs = mat.get_editor_property('expression_collection').get_editor_property('expressions')
    except Exception:
        return None
    for e in exprs:
        if e is None:
            continue
        cn = e.get_class().get_name()
        kinds[cn] = kinds.get(cn, 0) + 1
        try:
            name = str(e.get_editor_property('name')) if hasattr(e, 'get_editor_property') else ''
        except Exception:
            name = ''
        if cn == 'MaterialExpressionTextureSample':
            t = None
            try:
                t = e.get_editor_property('texture')
            except Exception:
                pass
            textures.append({'node': name, 'tex': tex_info(t), 'sampler_type': str(e.get_editor_property('samples_type')) if hasattr(e, 'get_editor_property') else ''})
        elif cn == 'MaterialExpressionScalarParameter':
            params['scalar'].append(name)
        elif cn == 'MaterialExpressionVectorParameter':
            params['vector'].append(name)
        elif cn == 'MaterialExpressionTextureParameter':
            params['texture'].append(name)
        elif cn == 'MaterialExpressionStaticSwitchParameter':
            params['switch'].append(name)
    return {'expr_total': sum(kinds.values()), 'kinds_top': dict(sorted(kinds.items(), key=lambda kv: -kv[1])[:12]),
            'textures': textures, 'params': params}

for n in CRATE_MATS:
    m = u.load_asset(MAT_DIR + n)
    if m is None:
        out['crate_materials'][n] = 'MISSING'
        continue
    rec = {'class': m.get_class().get_name()}
    for prop in ('blend_mode', 'shading_model', 'two_sided', 'used_with_skeletal_mesh', 'used_with_static_mesh'):
        try:
            rec[prop] = str(m.get_editor_property(prop))
        except Exception:
            pass
    rec['graph'] = walk(m)
    out['crate_materials'][n] = rec

for n in RITUAL_MATS + [MARBLE.split('/')[-1]]:
    path = (RITUAL_DIR if n.startswith('MI_') and n != 'MI_Chest_Ziarat_4K' else RUNTIME_DIR if n.startswith('Surface_') else '/Game/ColdSteelUI/Warehouse20260909/ZiaratWhiteMarble/') + n
    if n in RUNTIME_MATS:
        path = RUNTIME_DIR + n
    m = u.load_asset(path)
    if m is None:
        out['ritual_materials'][n] = 'MISSING:' + path
        continue
    rec = {'class': m.get_class().get_name(), 'path': path}
    try:
        p = m.get_editor_property('parent') if rec['class'] != 'Material' else None
        rec['parent'] = p.get_path_name() if p else None
        if p is not None:
            rec['parent_graph'] = walk(p)
    except Exception as exc:
        rec['parent_err'] = str(exc)[:80]
    if rec['class'] == 'Material':
        rec['graph'] = walk(m)
    out['ritual_materials'][n] = rec

with open(r'D:\FPS3D\FPSGAME\SourceAssets\WarehouseCrateTiers20260924\probes\material_inventory.json', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print('MATERIAL_INVENTORY_DONE', flush=True)
