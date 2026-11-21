"""Material authoring for the village woodworking bench, using an isolated asset host."""
import json
from pathlib import Path
import unreal as ue

HERE = Path(__file__).resolve().parent
OUTPUT = '/Game/Building/WoodworkingCrystalBench/Surfaces'
CHAPEL = '/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelTimber_'
CARPENTER = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_Carpenter'
ARCANE = '/Game/Building/ArcaneWorkbenchV6_20261107/Materials/'
MATERIALS = {
    'oak': OUTPUT + '/M_WorkshopOiledOak',
    'endgrain': CARPENTER + 'Cut',
    'iron': CARPENTER + 'Iron',
    'steel': CARPENTER + 'Steel',
    'brass': CARPENTER + 'Brass',
    'crystal': OUTPUT + '/M_WorkshopDriveCrystal',
    'leather': ARCANE + 'M_EW_Leather_dark_worn_binding',
}
L = ue.MaterialEditingLibrary
E = ue.EditorAssetLibrary
A = ue.AssetToolsHelpers.get_asset_tools()

def start(key):
    name = MATERIALS[key].split('/')[-1]
    m = ue.find_object(None, MATERIALS[key] + '.' + name)
    if not m:
        m = ue.load_asset(MATERIALS[key]) if E.does_asset_exist(MATERIALS[key]) else A.create_asset(
            name, OUTPUT, ue.Material, ue.MaterialFactoryNew())
    if not m:
        raise RuntimeError('Cannot author ' + name)
    # UE 5.8's bulk delete removes elements from the same array it iterates.
    # Work from a snapshot so stale expressions and their inputs cannot survive.
    for expression in reversed(list(L.get_material_expressions(m))):
        L.delete_material_expression(m, expression)
    m.set_editor_property('used_with_instanced_static_meshes', True)
    return m

def node(m, name):
    return L.create_material_expression(m, getattr(ue, 'MaterialExpression' + name))

def link(src, channel, dest, pin):
    if not L.connect_material_expressions(src, channel, dest, pin):
        raise RuntimeError('Could not link pin ' + pin)

def output(expr, channel, property_name):
    if not L.connect_material_property(expr, channel, getattr(ue.MaterialProperty, 'MP_' + property_name)):
        raise RuntimeError('Could not bind ' + property_name)

def local_position(m):
    p = node(m, 'TransformPosition')
    p.set_editor_property('transform_source_type', ue.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    p.set_editor_property('transform_type', ue.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    link(node(m, 'WorldPosition'), '', p, '')
    return p

def custom(m, label, width, code, connections):
    c = node(m, 'Custom')
    c.set_editor_property('description', label)
    c.set_editor_property('code', code.strip())
    c.set_editor_property('output_type', getattr(ue.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    pins = []
    for name, src, channel in connections:
        entry = ue.CustomInput()
        entry.set_editor_property('input_name', name)
        pins.append(entry)
    c.set_editor_property('inputs', pins)
    for name, src, channel in connections:
        link(src, channel, c, name)
    return c

def sample(m, suffix, sampler):
    path = CHAPEL + suffix
    tex = ue.load_asset(path)
    if not tex:
        raise RuntimeError('Missing oak scan ' + path)
    t = node(m, 'TextureSample')
    t.set_editor_property('texture', tex)
    t.set_editor_property('sampler_type', getattr(ue.MaterialSamplerType, 'SAMPLERTYPE_' + sampler))
    return t

def finish(m):
    L.layout_material_expressions(m)
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError('Material compile failed ' + str(errors))
    if not ue.EditorLoadingAndSavingUtils.save_packages([m.get_outer()], False):
        raise RuntimeError('Save failed ' + m.get_path_name())
    return m.get_path_name().split('.')[0]

def wood():
    # Same scan and UV orientation as the blacksmith's furniture. On the table the
    # active feed zone and outside lip carry a waxed, partially burnished finish.
    m = start('oak')
    color = sample(m, 'Color', 'COLOR')
    normal = sample(m, 'NormalDX', 'NORMAL')
    packed = sample(m, 'ARH', 'MASKS')
    accent = custom(m, 'Handling on the work surface, centimeters', 1, """
        float height = 1.0 - smoothstep(0.8, 7.0, abs(P.z - 95.4));
        float outer = smoothstep(63., 107., max(abs(P.x), abs(P.y)));
        float work = 1.0 - smoothstep(21., 65., length(P.xy * float2(0.75,1.0)));
        float wear = height * (0.18 + 0.64 * max(outer,work));
        return saturate(wear * (0.68 + 0.30 * Grain));
    """, [('P', local_position(m), ''), ('Grain', packed, 'G')])
    base = custom(m, 'Brown oiled oak and handled grain', 3, """
        float3 oil = Grain * float3(0.88, 0.77, 0.63);
        return oil * lerp(float3(1.,1.,1.), float3(1.15,1.09,1.02), W);
    """, [('Grain', color, 'RGB'), ('W', accent, '')])
    rough = custom(m, 'Wax and open pores', 1, """
        return saturate(lerp(0.32 + 0.53 * Grain, 0.24 + 0.31 * Grain, W));
    """, [('Grain', packed, 'G'), ('W', accent, '')])
    output(base, '', 'BASE_COLOR')
    output(rough, '', 'ROUGHNESS')
    output(normal, 'RGB', 'NORMAL')
    output(packed, 'R', 'AMBIENT_OCCLUSION')
    return finish(m)

def crystal():
    # A solid optical body with internal cleavage under the facets. The ray
    # offset moves inclusions under camera motion without a translucent overdraw pass.
    m = start('crystal')
    v = node(m, 'Transform')
    v.set_editor_property('transform_source_type', ue.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
    v.set_editor_property('transform_type', ue.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
    link(node(m, 'CameraVectorWS'), '', v, '')
    n = node(m, 'Transform')
    n.set_editor_property('transform_source_type', ue.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
    n.set_editor_property('transform_type', ue.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
    link(node(m, 'PixelNormalWS'), '', n, '')
    facets = custom(m, 'Light transmitted through each cut face', 1, """
        float3 normal = normalize(N);
        float3 view = normalize(V);
        float alignment = .5 + .5*dot(normal, normalize(float3(-.79,.56,.31)));
        float facing = saturate(dot(normal,view));
        return saturate(.07 + .72*alignment*alignment + .19*facing*facing);
    """, [('N', n, ''), ('V', v, '')])
    zones = custom(m, 'Growth bands and two internal cleavage planes', 3, """
        float3 ray = normalize(ViewDir + 0.000001);
        float3 shallow = P - ray * 0.85;
        float3 deep = P - ray * 2.45;
        float growth = dot(deep,float3(.062,.029,.114)) + .09*sin(dot(deep,float3(.24,.08,.05)));
        float band = .5 + .5*cos(growth*6.283185);
        float a = dot(shallow,float3(.118,-.065,.089)) + .052*sin(shallow.z*.57 + shallow.x*.11);
        float b = dot(deep,float3(-.075,.163,.022)) + .037*sin(deep.y*.36 - deep.z*.22);
        float aw = clamp(fwidth(a),.005,.14);
        float bw = clamp(fwidth(b),.005,.14);
        float va = 1.0-smoothstep(.009,.023+aw,abs(frac(a)-.5));
        float vb = 1.0-smoothstep(.006,.019+bw,abs(frac(b)-.5));
        float fissure = saturate(va*.66*smoothstep(.15,.88,band) + vb*.34*(1.-band));
        return float3(band,fissure,saturate(Rim));
    """, [('P', local_position(m), ''), ('ViewDir', v, ''), ('Rim', node(m,'Fresnel'), '')])
    base = custom(m, 'Blue green mineral and pale fracture faces', 3, """
        float3 body = lerp(float3(.008,.046,.059),float3(.025,.15,.146),Face);
        body *= .86 + .18*Zones.x;
        return lerp(body,float3(.055,.23,.205),.24*Zones.y + .12*Zones.z);
    """, [('Zones', zones, ''), ('Face', facets, '')])
    drive = node(m, 'ScalarParameter')
    drive.set_editor_property('parameter_name', 'DriveStrength')
    drive.set_editor_property('default_value', 1.0)
    glow = custom(m, 'Low mineral glow inside the facets', 3, """
        float breath = .97 + .03 * sin(T * .79);
        float flux = (.23 + 2.8*Face*Face)*(.79 + .27*Zones.x);
        flux += .71*Zones.y + .19*Zones.z;
        // Limit the interior glow as eyes adapt in the shadow of the bench.
        // The mineral still responds to incident lighting and the saw drive.
        float3 color = lerp(float3(.018,.63,.86),float3(.11,.88,.82),Face);
        return color * flux * breath * clamp(Power,0.,2.) / max(Exposure,1.);
    """, [('Zones', zones, ''), ('Face', facets, ''), ('Power', drive, ''),
          ('T', node(m,'Time'), ''), ('Exposure', node(m,'EyeAdaptation'), '')])
    rough = custom(m, 'Cleaved face roughness', 1,
                   'return .27 + .08*Zones.x + .07*Zones.y;', [('Zones', zones, '')])
    specular = node(m, 'Constant')
    specular.set_editor_property('r', .32)
    output(base,'','BASE_COLOR')
    output(glow,'','EMISSIVE_COLOR')
    output(rough,'','ROUGHNESS')
    output(specular,'','SPECULAR')
    return finish(m)

if __name__ == '__main__':
    authored = [wood(), crystal()]
    (HERE/'packages.json').write_text(json.dumps(authored, indent=2), encoding='utf-8')
    (HERE/'bindings-staged.json').write_text(json.dumps(MATERIALS, indent=2), encoding='utf-8')
    ue.log('CRYSTAL_BENCH_SURFACES_SAVED ' + str(authored))
