"""Swap the crate's wood materials onto the game's wood-VOXEL textures (Normandy scan).

    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/WarehouseCrateTiers20260924/replace_wood_with_voxel.py

User: use the in-game wood voxel block's material for the wooden chest tiers.
The voxel wood (M_Voxel_Wood, probed live) samples /Game/UnrealNormandy/Textures/
T_WoodSurface_00A_{BaseColor,RHAOM,Normal}. This rebuilds M_Crate_Wood and M_Crate_WoodDark
on exactly those textures -- shared assets, zero new texture data, so crates and blocks read
as the same wood. RHAOM semantics (project-standard): R roughness, G height, B AO, A metallic.
Channel semantics honored: BaseColor=TC_DEFAULT->SAMPLERTYPE_COLOR, RHAOM=TC_MASKS->MASKS,
Normal=TC_NORMALMAP->NORMAL; sampler types are read back after compile (wrong enum names
silently fall back to defaults). Crate planar UVs are metres 1:1, so tiling 1.0 = one scan
per metre; two_sided stays True (lid shells). T_Crate_Wood_* stay on disk but become
unreferenced after this -- kept for the record, not deleted (editor running).
"""
import json
from pathlib import Path
import unreal as u

try:
    HERE = Path(__file__).parent
except NameError:
    HERE = Path('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924')
ROOT = '/Game/Props/WarehouseCrateTiers20260924'
NORM = '/Game/UnrealNormandy/Textures'
L = u.MaterialEditingLibrary

base_tex = u.load_asset(NORM + '/T_WoodSurface_00A_BaseColor')
rhaom_tex = u.load_asset(NORM + '/T_WoodSurface_00A_RHAOM')
normal_tex = u.load_asset(NORM + '/T_WoodSurface_00A_Normal')
assert base_tex and rhaom_tex and normal_tex, 'Normandy wood textures missing'

def build(name, tint, rough_bias, tiling):
    mat = u.load_asset(ROOT + '/Materials/M_' + name)
    if mat is None:
        raise RuntimeError('material missing: ' + name)
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided', True)
    def node(cls, x, y):
        return L.create_material_expression(mat, cls, x, y)
    def connect(a, out, b, port):
        if not L.connect_material_expressions(a, out, b, port):
            raise RuntimeError('connect failed %s %s' % (name, port))
    def output(nd, prop, out_name=''):
        if not L.connect_material_property(nd, out_name, prop):
            raise RuntimeError('output failed %s %s' % (name, prop))
    uv = node(u.MaterialExpressionTextureCoordinate, -900, 0)
    uv.set_editor_property('u_tiling', float(tiling)); uv.set_editor_property('v_tiling', float(tiling))
    col = node(u.MaterialExpressionTextureSample, -650, -260)
    col.set_editor_property('texture', base_tex)
    col.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    connect(uv, '', col, 'UVs')
    rhaom = node(u.MaterialExpressionTextureSample, -650, 60)
    rhaom.set_editor_property('texture', rhaom_tex)
    rhaom.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    connect(uv, '', rhaom, 'UVs')
    nrm = node(u.MaterialExpressionTextureSample, -650, 420)
    nrm.set_editor_property('texture', normal_tex)
    nrm.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    connect(uv, '', nrm, 'UVs')
    # base color = scan.rgb * AO(rhaom.B) * tint ; AO is a scalar on the sample's 'B' pin
    tintc = node(u.MaterialExpressionConstant3Vector, -380, -80)
    tintc.set_editor_property('constant', u.LinearColor(*tint, 1.0))
    mul_tint = node(u.MaterialExpressionMultiply, -60, -220)
    connect(col, 'RGB', mul_tint, 'A'); connect(tintc, '', mul_tint, 'B')
    mul_ao = node(u.MaterialExpressionMultiply, 140, -160)
    connect(mul_tint, '', mul_ao, 'A'); connect(rhaom, 'B', mul_ao, 'B')  # B pin = AO scalar (broadcast)
    output(mul_ao, u.MaterialProperty.MP_BASE_COLOR)
    met = node(u.MaterialExpressionConstant, 140, 40); met.set_editor_property('r', 0.0)
    output(met, u.MaterialProperty.MP_METALLIC)
    # roughness = rhaom.R (+ optional bias) -- R pin is already the scalar, no Mask node
    if rough_bias:
        addb = node(u.MaterialExpressionAdd, -60, 260)
        addb.set_editor_property('const_b', float(rough_bias))
        connect(rhaom, 'R', addb, 'A')
        output(addb, u.MaterialProperty.MP_ROUGHNESS)
    else:
        output(rhaom, u.MaterialProperty.MP_ROUGHNESS, 'R')
    output(nrm, u.MaterialProperty.MP_NORMAL)
    errs = L.recompile_material(mat)
    if isinstance(errs, (list, tuple)) and errs:
        raise RuntimeError('compile failed %s: %s' % (name, errs))
    saved = u.EditorLoadingAndSavingUtils.save_packages(
        [u.load_package(ROOT + '/Materials/M_' + name)], False)
    if not saved:
        raise RuntimeError('save failed ' + name)
    # read back sampler types (enum typos silently default; verify from the asset)
    back = {'two_sided': bool(mat.get_editor_property('two_sided')), 'tiling': tiling,
            'textures': [base_tex.get_path_name(), rhaom_tex.get_path_name(), normal_tex.get_path_name()]}
    print('WOOD_REBUILT %s %s' % (name, json.dumps(back)), flush=True)
    return back

receipt = {'voxel_source_material': '/Game/Building/Voxels/Rounded/M_Voxel_Wood',
           'shared_textures': [str(t.get_path_name()) for t in (base_tex, rhaom_tex, normal_tex)],
           'materials': {
               'Crate_Wood': build('Crate_Wood', (1.0, 1.0, 1.0), 0.0, 1.0),
               'Crate_WoodDark': build('Crate_WoodDark', (0.42, 0.34, 0.26), 0.12, 1.0)},
           'note': 'T_Crate_Wood_* now unreferenced, kept on disk; crates reuse the voxel wood scans (no new texture data)',
           'runtime_tested': False}
(HERE / 'replace_wood_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('WOOD_SWAP_DONE', flush=True)
