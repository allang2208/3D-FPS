"""Draw the village road on the terrain mesh using the authored road mask."""
from pathlib import Path
import runpy

import unreal as u


TAG = 'VillageTerrainRoad'
ROAD = '/Game/UnrealNormandy/Textures/T_LC_GroundRockyRoad_00A_'
SOIL = '/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_'
MASK = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/T_VillageRoadMask'
LAYERS = {'BASE_COLOR': 'return', 'NORMAL': 'RoadNormal', 'ROUGHNESS': 'RoadRoughness'}


def add_to_ground(mat, plan):
    lib = u.MaterialEditingLibrary
    fit_yard = runpy.run_path(str(Path(__file__).with_name('smith_yard_material.py')))['bind']
    turf = runpy.run_path(str(Path(__file__).with_name('village_turf_material.py')))['add_turf']
    scan = runpy.run_path(str(Path(__file__).with_name('village_ground_uv.py')))

    def node(cls):
        result = lib.create_material_expression(mat, cls)
        result.set_editor_property('desc', TAG)
        return result

    def connect(source, channel, target, pin):
        if not lib.connect_material_expressions(source, channel, target, pin):
            raise RuntimeError('Cannot connect village road input ' + pin)

    expressions = lib.get_material_expressions(mat)
    if any(expr.get_editor_property('desc') == TAG for expr in expressions):
        updated = scan['update_saved_nodes'](mat,plan)
        turf_updated=turf(mat,plan)
        return fit_yard(mat) or turf_updated or updated
    mat.modify()
    def parameter(cls, name, value):
        expr = next((item for item in expressions if isinstance(item, cls)
                     and str(item.get_editor_property('parameter_name')) == name), None)
        if expr is None:
            expr = node(cls)
            expr.set_editor_property('parameter_name', name)
            expr.set_editor_property('default_value', value)
        return expr

    pose = parameter(u.MaterialExpressionVectorParameter, 'VillageRoadPose', u.LinearColor(0, 0, 0, 0))
    # A zero axis means the world has no placed village, including material previews.
    pose.set_editor_property('default_value', u.LinearColor(0, 0, 0, 0))
    inputs = {
        'Position': (node(u.MaterialExpressionWorldPosition), ''),
        'OriginAndCos': (pose, ''), 'SinYaw': (pose, 'A'),
        'Width': (parameter(u.MaterialExpressionScalarParameter, 'RoadEdgeFadeCm', 110.), ''),
        'Breakup': (parameter(u.MaterialExpressionScalarParameter, 'RoadEdgeBreakupCm', 48.), ''),
    }
    for name, path in {
        'RoadMask': MASK, 'RoadB': ROAD + 'Albedo', 'RoadN': ROAD + 'Normal',
        'RoadORM': ROAD + 'RHAOM', 'SoilB': SOIL + 'B', 'SoilN': SOIL + 'N',
        'SoilORM': SOIL + 'ORM', 'SoilH': SOIL + 'H',
    }.items():
        texture = u.load_asset(path)
        if not texture:
            raise RuntimeError('Missing road texture ' + path)
        obj = node(u.MaterialExpressionTextureObject)
        obj.set_editor_property('texture', texture)
        # The RVT writer uses the same textures. Keep its actual sampler types,
        # including the Alpha-compressed chapel height map.
        existing = next(expr for expr in expressions if isinstance(expr, u.MaterialExpressionTextureSample)
                        and expr.get_editor_property('texture') == texture)
        obj.set_editor_property('sampler_type', existing.get_editor_property('sampler_type'))
        inputs[name] = (obj, '')

    ex, ey = plan.get('surface_extent_m', plan['extent_m'])
    edge = runpy.run_path(str(Path(__file__).with_name('village_road_blend.py')))['EDGE_CODE']
    code = '''
struct FVillageEdge
{
    float2 Weights(float3 M, float2 UV, float H, float2 Span, float Width, float Breakup)
    {
        EDGE_FUNCTION
    }
};
RoadNormal = float3(0,0,1);
RoadRoughness = 0;
Coverage = 0;
float2 axis = float2(OriginAndCos.z, SinYaw);
float2 delta = Position.xy - OriginAndCos.xy;
float2 local = float2(dot(delta,axis), dot(delta,float2(-axis.y,axis.x)));
float2 span = float2(SPAN_X,SPAN_Y);
float2 uv = local/span + .5;
float2 dx = ddx(local), dy = ddy(local);
[branch] if (dot(axis,axis)<.5 || any(uv<=0) || any(uv>=1)) return float3(0,0,0);
float3 mask = Texture2DSampleGrad(RoadMask,GetMaterialSharedSampler(RoadMaskSampler,Material.Clamp_WorldGroupSettings),uv,dx/span,dy/span).rgb;
float2 soilUV = (local+span*.5)/SOIL_TILE, roadUV = (local+span*.5)/320.;
float height = ProcessMaterialAlphaTextureLookup(SAMPLE_SOIL(SoilH)).r;
FVillageEdge edge;
float2 w = edge.Weights(mask,uv,height,span,Width,Breakup);
Coverage = max(w.x,w.y);
[branch] if (Coverage<=0) return float3(0,0,0);
float roadWeight = saturate(w.x/max(.0001,Coverage));
float3 n = normalize(lerp(UnpackNormalMap(SAMPLE_SOIL(SoilN)),UnpackNormalMap(SAMPLE_ROAD(RoadN)),roadWeight));
RoadNormal = float3(n.x*axis.x-n.y*axis.y,n.x*axis.y+n.y*axis.x,n.z);
RoadRoughness = lerp(SAMPLE_SOIL(SoilORM).g,SAMPLE_ROAD(RoadORM).r,roadWeight);
return lerp(SAMPLE_SOIL(SoilB).rgb,SAMPLE_ROAD(RoadB).rgb,roadWeight);
'''
    for family, names, uv, tile in (
        ('SOIL', ('SoilB', 'SoilN', 'SoilORM', 'SoilH'), 'soilUV', 'SOIL_TILE'),
        ('ROAD', ('RoadB', 'RoadN', 'RoadORM'), 'roadUV', '320.'),
    ):
        for name in names:
            sample = (f'Texture2DSampleGrad({name},GetMaterialSharedSampler({name}Sampler,'
                      f'Material.Wrap_WorldGroupSettings),{uv},dx/{tile},dy/{tile})')
            code = code.replace(f'SAMPLE_{family}({name})', sample)
    code = code.replace('EDGE_FUNCTION', edge).replace('SPAN_X', str(ex*200.)).replace('SPAN_Y', str(ey*200.))
    code = code.replace('SOIL_TILE', str(plan['ground_dressing']['earth_tile_m']*100.))
    code = scan['visible'](code)
    layer = node(u.MaterialExpressionCustom)
    layer.set_editor_property('code', code)
    types = u.CustomMaterialOutputType
    layer.set_editor_property('output_type', types.CMOT_FLOAT3)
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    layer.set_editor_property('inputs', pins)
    extra = []
    for name, kind in [('RoadNormal', types.CMOT_FLOAT3), ('RoadRoughness', types.CMOT_FLOAT1), ('Coverage', types.CMOT_FLOAT1)]:
        pin = u.CustomOutput()
        pin.set_editor_property('output_name', name)
        pin.set_editor_property('output_type', kind)
        extra.append(pin)
    layer.set_editor_property('additional_outputs', extra)
    for name, (source, channel) in inputs.items():
        connect(source, channel, layer, name)
    for name, channel in LAYERS.items():
        prop = getattr(u.MaterialProperty, 'MP_' + name)
        original = lib.get_material_property_input_node(mat, prop)
        original_channel = lib.get_material_property_input_node_output_name(mat, prop)
        mix = node(u.MaterialExpressionLinearInterpolate)
        connect(original, original_channel, mix, 'A')
        connect(layer, channel, mix, 'B')
        connect(layer, 'Coverage', mix, 'Alpha')
        if not lib.connect_material_property(mix, '', prop):
            raise RuntimeError('Cannot connect village road to ' + name)
    scan['update_saved_nodes'](mat,plan)
    turf(mat,plan)
    fit_yard(mat)
    return True
