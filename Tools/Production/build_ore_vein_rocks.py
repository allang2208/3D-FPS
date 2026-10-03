"""Ore vein rock family (2026-09-30, user request): one shared rock mesh shape,
per-mineral surface treatment. Builds:

  M_HillsOreRock         master material: CliffSurface rock base + procedural
                         vein mask (world-space gradient noise band + voronoi
                         crystal specks) that tints color/metallic/roughness.
  MI_HillsOre_Iron/Copper/Silver/Gold   parameter overrides per mineral.
  SM_LS_Rock_00A_Iron/Copper/Silver/Gold  duplicated rock mesh, slot 0 = MI.

Run with UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this>
-unattended -NullRHI -nosplash. Commandlet does not compile shaders; verify
in-editor or via DDC fill afterwards.
"""
import unreal

DEST = '/Game/WorldGeneration/TemperateHills/OreRocks'
lib = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

ALBEDO = unreal.load_asset('/Game/UnrealNormandy/Textures/T_CliffSurface_03A_BaseColor')
NORMAL = unreal.load_asset('/Game/UnrealNormandy/Textures/T_CliffSurface_03A_Normal')
RHAOM = unreal.load_asset('/Game/UnrealNormandy/Textures/T_CliffSurface_03A_RHAOM')
assert ALBEDO and NORMAL and RHAOM, 'CliffSurface textures missing'


def sampler_type_for(tex, want_normal=False):
    """Sampler type must follow the texture's own compression settings, not a guess."""
    if want_normal:
        return unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
    cs = tex.get_editor_property('compression_settings')
    if cs == unreal.TextureCompressionSettings.TC_MASKS:
        return unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
    if not tex.get_editor_property('srgb'):
        return unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
    return unreal.MaterialSamplerType.SAMPLERTYPE_COLOR


def expr(m, cls, **props):
    e = lib.create_material_expression(m, cls)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def link(a, b, out='', inp=''):
    assert lib.connect_material_expressions(a, out, b, inp), 'connect failed'


def build_master():
    m = unreal.load_asset(DEST + '/M_HillsOreRock') or tools.create_asset(
        'M_HillsOreRock', DEST, unreal.Material, unreal.MaterialFactoryNew())
    for e in list(lib.get_material_expressions(m)):
        lib.delete_material_expression(m, e)

    # --- vein mask, world-space so every instance veins differently ---
    wp = expr(m, unreal.MaterialExpressionWorldPosition)
    # Burned-in constants (not parameters): immune to the runtime
    # parameter-reads-zero pathology this project has hit before, and free.
    scale = expr(m, unreal.MaterialExpressionConstant, r=0.012)
    wp_scaled = expr(m, unreal.MaterialExpressionMultiply)
    link(wp, wp_scaled, inp='A'); link(scale, wp_scaled, inp='B')
    noise1 = expr(m, unreal.MaterialExpressionNoise,
                  noise_function=unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_ALU,
                  # Perf 2026-09-30: the mask is thresholded downstream, so quality 1 and
                  # one octave less are visually indistinguishable at a fraction of the cost.
                  levels=4, quality=1)
    link(wp_scaled, noise1, inp='World Position')
    band = expr(m, unreal.MaterialExpressionSaturate)
    n1_lo = expr(m, unreal.MaterialExpressionConstant, r=0.46)
    sub1 = expr(m, unreal.MaterialExpressionSubtract)
    link(noise1, sub1, inp='A'); link(n1_lo, sub1, inp='B')
    span1 = expr(m, unreal.MaterialExpressionConstant, r=0.26)
    div1 = expr(m, unreal.MaterialExpressionDivide)
    link(sub1, div1, inp='A'); link(span1, div1, inp='B')
    link(div1, band)

    scale2 = expr(m, unreal.MaterialExpressionConstant, r=0.055)
    wp_scaled2 = expr(m, unreal.MaterialExpressionMultiply)
    link(wp, wp_scaled2, inp='A'); link(scale2, wp_scaled2, inp='B')
    noise2 = expr(m, unreal.MaterialExpressionNoise,
                  noise_function=unreal.NoiseFunction.NOISEFUNCTION_VORONOI_ALU,
                  # Perf 2026-09-30: one octave keeps the round cell specks; each extra
                  # Voronoi octave costs another 27-cell search per pixel.
                  levels=1, quality=1)
    link(wp_scaled2, noise2, inp='World Position')
    speck = expr(m, unreal.MaterialExpressionSaturate)
    n2_lo = expr(m, unreal.MaterialExpressionConstant, r=0.74)
    sub2 = expr(m, unreal.MaterialExpressionSubtract)
    link(noise2, sub2, inp='A'); link(n2_lo, sub2, inp='B')
    span2 = expr(m, unreal.MaterialExpressionConstant, r=0.12)
    div2 = expr(m, unreal.MaterialExpressionDivide)
    link(sub2, div2, inp='A'); link(span2, div2, inp='B')
    link(div2, speck)
    speck_amt = expr(m, unreal.MaterialExpressionConstant, r=0.3)
    speck_mul = expr(m, unreal.MaterialExpressionMultiply)
    link(speck, speck_mul, inp='A'); link(speck_amt, speck_mul, inp='B')
    mask = expr(m, unreal.MaterialExpressionSaturate)
    addv = expr(m, unreal.MaterialExpressionAdd)
    link(band, addv, inp='A'); link(speck_mul, addv, inp='B')
    link(addv, mask)

    # --- rock base textures, projected in object space (NO mesh UV) ---
    # 2026-10-02 fix: the Normandy rock family ships unmaintained UV0 (its own
    # vertex-blend material never uses TexCoord), so UV0 sampling collapsed to a
    # single constant texel = flat grey rock. Project the textures from the
    # local position (world position minus object pivot, per-instance on ISMs)
    # on two planes (top XY, front XZ). Two taps per texture (6 total) stays
    # cheaper than the stock vertex-blend rock.
    obj_pos = expr(m, unreal.MaterialExpressionObjectPositionWS)
    local = expr(m, unreal.MaterialExpressionSubtract)
    link(wp, local, inp='A'); link(obj_pos, local, inp='B')
    tex_scale = expr(m, unreal.MaterialExpressionConstant, r=0.006)

    # Top-vs-side blend from the LOCAL position, not PixelNormalWS: any
    # world-space normal node inside the Normal input's tree is rejected by the
    # translator ("Invalid node PixelNormalWS used for Normal input"), which
    # failed the whole material down to the default grey. blend = 1.6*|z| / (|y|+|z|)
    loc_y = expr(m, unreal.MaterialExpressionComponentMask, R=False, G=True, B=False, A=False)
    link(local, loc_y)
    loc_z = expr(m, unreal.MaterialExpressionComponentMask, R=False, G=False, B=True, A=False)
    link(local, loc_z)
    abs_y = expr(m, unreal.MaterialExpressionAbs); link(loc_y, abs_y)
    abs_z = expr(m, unreal.MaterialExpressionAbs); link(loc_z, abs_z)
    blend_top = expr(m, unreal.MaterialExpressionSaturate)
    denom = expr(m, unreal.MaterialExpressionAdd)
    link(abs_y, denom, inp='A'); link(abs_z, denom, inp='B')
    eps = expr(m, unreal.MaterialExpressionConstant, r=1.0)
    denom2 = expr(m, unreal.MaterialExpressionAdd)
    link(denom, denom2, inp='A'); link(eps, denom2, inp='B')
    ratio = expr(m, unreal.MaterialExpressionDivide)
    link(abs_z, ratio, inp='A'); link(denom2, ratio, inp='B')
    ratio_gain = expr(m, unreal.MaterialExpressionMultiply)
    gain = expr(m, unreal.MaterialExpressionConstant, r=1.6)
    link(ratio, ratio_gain, inp='A'); link(gain, ratio_gain, inp='B')
    link(ratio_gain, blend_top)

    def projected_pair(tex, want_normal=False):
        uv_a = expr(m, unreal.MaterialExpressionComponentMask, R=True, G=True, B=False, A=False)
        link(local, uv_a)
        uv_a_s = expr(m, unreal.MaterialExpressionMultiply)
        link(uv_a, uv_a_s, inp='A'); link(tex_scale, uv_a_s, inp='B')
        uv_b = expr(m, unreal.MaterialExpressionComponentMask, R=False, G=True, B=True, A=False)
        link(local, uv_b)
        uv_b_s = expr(m, unreal.MaterialExpressionMultiply)
        link(uv_b, uv_b_s, inp='A'); link(tex_scale, uv_b_s, inp='B')
        sample_a = expr(m, unreal.MaterialExpressionTextureSample, texture=tex)
        sample_a.set_editor_property('sampler_type', sampler_type_for(tex, want_normal))
        link(uv_a_s, sample_a, inp='UVs')
        sample_b = expr(m, unreal.MaterialExpressionTextureSample, texture=tex)
        sample_b.set_editor_property('sampler_type', sampler_type_for(tex, want_normal))
        link(uv_b_s, sample_b, inp='UVs')
        mixed = expr(m, unreal.MaterialExpressionLinearInterpolate)
        link(sample_a, mixed, inp='A'); link(sample_b, mixed, inp='B'); link(blend_top, mixed, inp='Alpha')
        return mixed

    t_albedo = projected_pair(ALBEDO)
    t_normal = projected_pair(NORMAL, want_normal=True)
    t_rhaom = projected_pair(RHAOM)

    # --- base color: rock -> shaded ore tint inside the mask ---
    ore_col = expr(m, unreal.MaterialExpressionVectorParameter,
                   parameter_name='OreColor',
                   default_value=unreal.LinearColor(0.45, 0.22, 0.13, 1.0))
    # Perf 2026-09-30: ore-brightness shimmer reuses noise1 (saturated) instead of a
    # third noise node; the tint now varies along the vein field, which reads natural.
    n1_sat = expr(m, unreal.MaterialExpressionSaturate)
    link(noise1, n1_sat)
    dark = expr(m, unreal.MaterialExpressionConstant, r=0.78)
    lite = expr(m, unreal.MaterialExpressionConstant, r=1.08)
    shade = expr(m, unreal.MaterialExpressionLinearInterpolate)
    link(dark, shade, inp='A'); link(lite, shade, inp='B'); link(n1_sat, shade, inp='Alpha')
    tinted = expr(m, unreal.MaterialExpressionMultiply)
    link(ore_col, tinted, inp='A'); link(shade, tinted, inp='B')
    base = expr(m, unreal.MaterialExpressionLinearInterpolate)
    link(t_albedo, base, inp='A'); link(tinted, base, inp='B'); link(mask, base, inp='Alpha')
    lib.connect_material_property(base, '', unreal.MaterialProperty.MP_BASE_COLOR)

    # --- metallic / roughness inside the mask only ---
    zero = expr(m, unreal.MaterialExpressionConstant, r=0.0)
    metallic_p = expr(m, unreal.MaterialExpressionScalarParameter,
                      parameter_name='OreMetallic', default_value=0.6)
    metallic = expr(m, unreal.MaterialExpressionLinearInterpolate)
    link(zero, metallic, inp='A'); link(metallic_p, metallic, inp='B'); link(mask, metallic, inp='Alpha')
    lib.connect_material_property(metallic, '', unreal.MaterialProperty.MP_METALLIC)

    rough_p = expr(m, unreal.MaterialExpressionScalarParameter,
                   parameter_name='OreRoughness', default_value=0.45)
    rhaom_r = expr(m, unreal.MaterialExpressionComponentMask, R=True, G=False, B=False, A=False)
    link(t_rhaom, rhaom_r)
    rough = expr(m, unreal.MaterialExpressionLinearInterpolate)
    link(rhaom_r, rough, inp='A'); link(rough_p, rough, inp='B'); link(mask, rough, inp='Alpha')
    lib.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)

    lib.connect_material_property(t_normal, '', unreal.MaterialProperty.MP_NORMAL)

    # --- optional faint glow for silver/gold MIs (default 0) ---
    glow_p = expr(m, unreal.MaterialExpressionScalarParameter,
                  parameter_name='VeinEmissive', default_value=0.0)
    glow = expr(m, unreal.MaterialExpressionMultiply)
    link(tinted, glow, inp='A'); link(glow_p, glow, inp='B')
    glow_m = expr(m, unreal.MaterialExpressionMultiply)
    link(glow, glow_m, inp='A'); link(mask, glow_m, inp='B')
    lib.connect_material_property(glow_m, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    # The rocks are Nanite meshes; without this usage flag the material cannot
    # compile for that usage and falls back to the default grey material in game.
    m.set_editor_property('used_with_nanite', True)
    lib.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m


MINERALS = {
    'Iron':   dict(color=(0.42, 0.20, 0.12), metallic=0.55, roughness=0.52, glow=0.0),
    'Copper': dict(color=(0.52, 0.24, 0.11), metallic=0.70, roughness=0.44, glow=0.0),
    'Silver': dict(color=(0.80, 0.83, 0.88), metallic=0.92, roughness=0.30, glow=0.012),
    'Gold':   dict(color=(0.95, 0.71, 0.22), metallic=0.95, roughness=0.24, glow=0.018),
}

master = build_master()
report = {}
for name, v in MINERALS.items():
    mi = unreal.load_asset(DEST + '/MI_HillsOre_' + name) or tools.create_asset(
        'MI_HillsOre_' + name, DEST, unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', master)
    lib.set_material_instance_vector_parameter_value(
        mi, 'OreColor', unreal.LinearColor(*v['color'], 1.0))
    lib.set_material_instance_scalar_parameter_value(mi, 'OreMetallic', v['metallic'])
    lib.set_material_instance_scalar_parameter_value(mi, 'OreRoughness', v['roughness'])
    lib.set_material_instance_scalar_parameter_value(mi, 'VeinEmissive', v['glow'])
    unreal.EditorAssetLibrary.save_loaded_asset(mi)
    report[name] = mi.get_path_name()

src = unreal.load_asset('/Game/UnrealNormandy/StaticMeshes/SM_LS_Rock_00A')
assert src, 'source rock mesh missing'
for name in MINERALS:
    path = DEST + '/SM_LS_Rock_00A_' + name
    dup = unreal.EditorAssetLibrary.duplicate_loaded_asset(src, path)
    if not dup:
        dup = unreal.load_asset(path)
    assert dup, 'duplicate failed for ' + name
    dup.set_material(0, unreal.load_asset(DEST + '/MI_HillsOre_' + name))
    unreal.EditorAssetLibrary.save_loaded_asset(dup)
    report['mesh_' + name] = dup.get_path_name()

# Read-back verification: slots and parameter values survive a fresh load.
ok = True
for name, v in MINERALS.items():
    mesh = unreal.load_asset(DEST + '/SM_LS_Rock_00A_' + name)
    slot = mesh.get_editor_property('static_materials')[0]
    mi = slot.get_editor_property('material_interface')
    col = lib.get_material_instance_vector_parameter_value(mi, 'OreColor')
    met = lib.get_material_instance_scalar_parameter_value(mi, 'OreMetallic')
    good = abs(col.r - v['color'][0]) < 1e-3 and abs(met - v['metallic']) < 1e-3
    ok &= good
    unreal.log('ORE_ROCK_VERIFY {} mesh={} mi={} color=({:.2f},{:.2f},{:.2f}) metallic={:.2f} {}'
               .format(name, mesh.get_name(), mi.get_name(), col.r, col.g, col.b, met,
                       'PASS' if good else 'FAIL'))
unreal.log('ORE_ROCK_BUILD_{}'.format('PASS' if ok else 'FAIL'))
