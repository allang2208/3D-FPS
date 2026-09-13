"""Author saturated red laser effects and the optical aperture, preserving gun coatings."""
import unreal as u
from pathlib import Path
import shutil
import json

O = Path(__file__).parent
D = '/Game/Weapons/TacticalDevices20260913'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
source = (O.parent/'WeaponAttachmentFinish20260913/import_finish.py').read_text()
exec(source[source.index('def save('):source.index('def is_target(')])

def target(path):
    local = O.parents[1]/'Content'/Path(path.removeprefix('/Game/')).with_suffix('.uasset')
    backup = O/'BeforeRedBrightness'/local.relative_to(O.parents[1]/'Content')
    if local.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local, backup)
    m = u.load_asset(path)
    if not m:
        raise RuntimeError('Missing material '+path)
    return m

for name, strength, opacity in ([] if globals().get('APERTURE_ONLY') else [('M_LaserDot', 24., 1.), ('M_LaserBeam', 12., .9)]):
    m = target(D+'/Effects/'+name)
    L.delete_all_material_expressions(m)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    c = node(m, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(strength, .001, .0005, 1.))
    output(c, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    if opacity < 1:
        m.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
        output(constant(m, opacity), '', u.MaterialProperty.MP_OPACITY)
    L.recompile_material(m)
    save(m)

for family in ['M4', 'AKM', 'QBZ191']:
    original = D+'/'+family+'/laser/M_'+family+'_laser_Body'
    destination = original+'_OpticalV2'
    m = u.load_asset(destination) or E.duplicate_asset(original, destination)
    if E.get_metadata_tag(m, 'RedApertureEmission') != 'v2_spatial':
        uv = node(m, u.MaterialExpressionTextureCoordinate, coordinate_index=0)
        tex = node(m, u.MaterialExpressionTextureSample,
                   texture=u.load_asset(D+'/Textures/T_laser_BaseColor'),
                   sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        link(uv, '', tex, 'UVs')
        gb = node(m, u.MaterialExpressionMax)
        link(tex, 'G', gb, 'A'); link(tex, 'B', gb, 'B')
        red = node(m, u.MaterialExpressionSubtract)
        link(tex, 'R', red, 'A'); link(gb, '', red, 'B')
        gain = node(m, u.MaterialExpressionMultiply, const_b=12.)
        link(red, '', gain, 'A')
        mask = node(m, u.MaterialExpressionClamp, min_default=0., max_default=1.)
        link(gain, '', mask, 'Input')
        # Generated base color contains stray red texels on the housing.
        # Color alone is not an optical-region mask: constrain it in mesh space.
        p = json.loads((O/'authoring.json').read_text())[family+'_laser']['emitter_blender_m']
        center = node(m, u.MaterialExpressionConstant3Vector,
                      constant=u.LinearColor(p[0]*100., -p[1]*100.-.2, p[2]*100., 1.))
        world = node(m, u.MaterialExpressionWorldPosition)
        local = node(m, u.MaterialExpressionTransformPosition,
                     transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                     transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        link(world, '', local, 'Input')
        distance = node(m, u.MaterialExpressionDistance)
        link(local, '', distance, 'A'); link(center, '', distance, 'B')
        radius = node(m, u.MaterialExpressionDivide, const_b=.65)
        link(distance, '', radius, 'A')
        falloff = node(m, u.MaterialExpressionOneMinus)
        link(radius, '', falloff, 'Input')
        aperture = node(m, u.MaterialExpressionClamp, min_default=0., max_default=1.)
        link(falloff, '', aperture, 'Input')
        optical_mask = node(m, u.MaterialExpressionMultiply)
        link(mask, '', optical_mask, 'A'); link(aperture, '', optical_mask, 'B')
        emission = node(m, u.MaterialExpressionMultiply)
        link(optical_mask, '', emission, 'A')
        color = node(m, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(16., .001, .0005, 1.))
        link(color, '', emission, 'B')
        output(emission, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
        E.set_metadata_tag(m, 'RedApertureEmission', 'v2_spatial')
    L.recompile_material(m)
    save(m)
u.log('LASER_RED_BRIGHTNESS_SAVED')
