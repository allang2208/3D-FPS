"""Fix the missing arch lid + upgrade crate material quality (v2 pass).

    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/WarehouseCrateTiers20260924/fix_crate_materials.py

Root cause of the missing half-round lid (user screenshot): the chest's lid shell is a
single-sided thin surface whose winding is inverted vs the body panels; the original
M_Ritual_Metal is two_sided=True (probed live), so the source always rendered it from the
back. Our M_Crate_* were one-sided -> the shell got culled and the arch "disappeared".
Fix: two_sided=True on the 7 structural materials (Gem stays one-sided closed solid).

Quality pass: re-import the v2 maps IN PLACE (replace_existing=True on textures updates the
same UTexture object; the ghost-package hazard is delete-then-reimport, not reimport), then
rebuild the 7 graphs: albedo now blends broad(R)+fine(G) channels, tuned roughness ranges
and linear albedo pairs, per-family specular. Verify: recompile clean, sampler types match
compression, two_sided reads back True.
"""
import json
from pathlib import Path
import unreal as u

try:
    HERE = Path(__file__).parent
except NameError:
    HERE = Path('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924')
ROOT = '/Game/Props/WarehouseCrateTiers20260924'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
receipt = {'textures': [], 'materials': {}, 'runtime_tested': False}

# ---------------------------------------------------------------- textures (reimport in place)
for family in ('Wood', 'Stone', 'Iron', 'Gold', 'Silver'):
    for suffix, normal in (('_Surface', False), ('_Normal', True)):
        name = 'T_Crate_%s%s' % (family, suffix)
        task = u.AssetImportTask(); task.filename = str(HERE / 'Textures' / (name + '.png'))
        task.destination_path = ROOT + '/Textures'; task.destination_name = name
        task.automated = True; task.replace_existing = True; task.save = False
        task.set_editor_property('async_', False)
        AT.import_asset_tasks([task])
        texture = u.load_asset(ROOT + '/Textures/' + name) or next(
            (a for a in task.get_objects() if isinstance(a, u.Texture2D)), None)
        if texture is None:
            raise RuntimeError('texture vanished on reimport: ' + name)
        texture.set_editor_property('srgb', False)
        texture.set_editor_property('compression_settings',
            u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS)
        want_cs = u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS
        if (texture.get_editor_property('srgb') is not False
                or texture.get_editor_property('compression_settings') != want_cs):
            raise RuntimeError('texture settings did not stick: ' + name)
        receipt['textures'].append(name)

# ---------------------------------------------------------------- materials
recipes = {  # name: (family, dark, bright, metallic, rmin, rmax, tiling, specular, two_sided)
    'Crate_Wood':     ('Wood', (.045, .022, .010), (.20, .105, .048), .0, .45, .68, 1.6, .35, True),
    'Crate_WoodDark': ('Wood', (.024, .012, .006), (.085, .048, .024), .0, .50, .72, 1.6, .35, True),
    'Crate_Stone':    ('Stone', (.055, .053, .050), (.235, .230, .215), .0, .70, .92, 2.2, .25, True),
    'Crate_Iron':     ('Iron', (.055, .056, .060), (.38, .385, .40), .85, .32, .58, 3.0, .55, True),
    'Crate_IronDark': ('Iron', (.020, .020, .022), (.062, .064, .070), .80, .45, .68, 3.0, .50, True),
    'Crate_Gold':     ('Gold', (.28, .15, .04), (.72, .47, .16), .95, .18, .34, 4.0, .60, True),
    'Crate_Silver':   ('Silver', (.20, .21, .23), (.60, .62, .66), .98, .08, .22, 3.5, .60, True),
}

def connect(a, out, b, port):
    if not L.connect_material_expressions(a, out, b, port):
        raise RuntimeError('connect failed ' + port)

def output(node, prop):
    if not L.connect_material_property(node, '', prop):
        raise RuntimeError('output failed ' + str(prop))

for name, (family, dark, bright, metal, rmin, rmax, tiling, specular, two_sided) in recipes.items():
    mat = u.load_asset(ROOT + '/Materials/M_' + name)
    if mat is None:
        raise RuntimeError('material missing (was not built?): ' + name)
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided', two_sided)
    def node(cls, x, y):
        return L.create_material_expression(mat, cls, x, y)
    surface = node(u.MaterialExpressionTextureSample, -470, 0)
    surface.set_editor_property('texture', u.load_asset(ROOT + '/Textures/T_Crate_%s_Surface' % family))
    surface.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    uv = node(u.MaterialExpressionTextureCoordinate, -700, 0)
    uv.set_editor_property('u_tiling', float(tiling)); uv.set_editor_property('v_tiling', float(tiling))
    connect(uv, '', surface, 'UVs')
    lo = node(u.MaterialExpressionConstant3Vector, -450, -320); lo.set_editor_property('constant', u.LinearColor(*dark, 1))
    hi = node(u.MaterialExpressionConstant3Vector, -450, -180); hi.set_editor_property('constant', u.LinearColor(*bright, 1))
    # albedo factor: 0.55*broad(R) + 0.45*fine(G), straight off the sample's channel outputs
    rs = node(u.MaterialExpressionMultiply, -160, -60); rs.set_editor_property('const_b', 0.55)
    connect(surface, 'R', rs, 'A')
    gs = node(u.MaterialExpressionMultiply, -160, 60); gs.set_editor_property('const_b', 0.45)
    connect(surface, 'G', gs, 'A')
    addf = node(u.MaterialExpressionAdd, -40, 0)
    connect(rs, '', addf, 'A'); connect(gs, '', addf, 'B')
    color = node(u.MaterialExpressionLinearInterpolate, 120, -230)
    connect(lo, '', color, 'A'); connect(hi, '', color, 'B'); connect(addf, '', color, 'Alpha')
    output(color, u.MaterialProperty.MP_BASE_COLOR)
    met = node(u.MaterialExpressionConstant, -150, -20); met.set_editor_property('r', metal)
    output(met, u.MaterialProperty.MP_METALLIC)
    rough = node(u.MaterialExpressionLinearInterpolate, -150, 150)
    rough.set_editor_property('const_a', rmin); rough.set_editor_property('const_b', rmax)
    connect(surface, 'B', rough, 'Alpha'); output(rough, u.MaterialProperty.MP_ROUGHNESS)
    spec = node(u.MaterialExpressionConstant, -150, 320); spec.set_editor_property('r', specular)
    output(spec, u.MaterialProperty.MP_SPECULAR)
    normal = node(u.MaterialExpressionTextureSample, -460, 520)
    normal.set_editor_property('texture', u.load_asset(ROOT + '/Textures/T_Crate_%s_Normal' % family))
    normal.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    connect(uv, '', normal, 'UVs'); output(normal, u.MaterialProperty.MP_NORMAL)
    errs = L.recompile_material(mat)
    if isinstance(errs, (list, tuple)) and errs:
        raise RuntimeError('compile failed %s: %s' % (name, errs))
    if bool(mat.get_editor_property('two_sided')) is not two_sided:
        raise RuntimeError('two_sided did not stick on ' + name)
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(ROOT + '/Materials/M_' + name)], False):
        raise RuntimeError('save failed ' + name)
    receipt['materials'][name] = {'two_sided': two_sided, 'tiling': tiling, 'rough': [rmin, rmax], 'spec': specular}

# Gem: closed solid, one-sided; rebuild the tiny untextured graph with a more polished roughness.
gem = u.load_asset(ROOT + '/Materials/M_Crate_Gem')
L.delete_all_material_expressions(gem)
gem.set_editor_property('two_sided', False)
def gnode(cls, x, y):
    return L.create_material_expression(gem, cls, x, y)
base = gnode(u.MaterialExpressionConstant3Vector, -200, -200); base.set_editor_property('constant', u.LinearColor(.012, .075, .40, 1))
output(base, u.MaterialProperty.MP_BASE_COLOR)
gmet = gnode(u.MaterialExpressionConstant, -200, -20); gmet.set_editor_property('r', 0.0); output(gmet, u.MaterialProperty.MP_METALLIC)
grgh = gnode(u.MaterialExpressionConstant, -200, 120); grgh.set_editor_property('r', 0.05); output(grgh, u.MaterialProperty.MP_ROUGHNESS)
gspc = gnode(u.MaterialExpressionConstant, -200, 240); gspc.set_editor_property('r', 0.8); output(gspc, u.MaterialProperty.MP_SPECULAR)
errs = L.recompile_material(gem)
if isinstance(errs, (list, tuple)) and errs:
    raise RuntimeError('compile failed Gem: %s' % errs)
if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(ROOT + '/Materials/M_Crate_Gem')], False):
    raise RuntimeError('save failed Gem')
receipt['materials']['Crate_Gem'] = {'two_sided': False, 'roughness': 0.05}

(HERE / 'fix_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('CRATE_FIX_DONE ' + json.dumps({'textures': len(receipt['textures']),
      'materials': len(receipt['materials'])}), flush=True)
