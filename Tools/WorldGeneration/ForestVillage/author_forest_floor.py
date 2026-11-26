"""Publish the sfjmafua Forest Floor scan to the existing hill / verge material slot."""
import json
import os
import runpy
from pathlib import Path

import unreal as u

shared = runpy.run_path(str(Path(__file__).with_name('author_wild_grass.py')))
load, save, wire = (shared[k] for k in ('load', 'save', 'wire'))
ed = u.MaterialEditingLibrary
assets = u.EditorAssetLibrary
folder = '/Game/ForestPathStudy/VillageRegion/ForestFloor'
trace_tag = 'Forest floor heightfield ray intersection'

# The three outputs describe one intersection: world-projected UV and positive depth.
# The unshifted derivatives keep height mips stable across the ray's loop exits.
TRACE = """
float2 uv = P.xy / Tile;
#if (!PIXELSHADER && !COMPUTESHADER) || RAYHITGROUPSHADER
return float3(uv, 0);
#else
float3 dx = ddx(P), dy = ddy(P);
float3 n = cross(dx, dy);
n *= rsqrt(max(dot(n,n), 1e-12));
n *= n.z < 0 ? -1 : 1;
float nv = saturate(dot(n, V));
float fade = (1-smoothstep(350,1200,DistanceCm)) * smoothstep(0.13,0.38,nv);
float depth = clamp(ReliefCm,0,3) * fade;
[branch] if (depth < 0.001) return float3(uv,0);
float rayCm = depth / max(nv,0.30);
float2 travel = V.xy * (rayCm / Tile);
float2 gx = dx.xy / Tile, gy = dy.xy / Tile;
int steps = (int)round(lerp(8.0,4.0,nv));
float previous = 0, previousGap = 1, t = 0, gap = 0;
[loop] for (int i=0; i<=steps; ++i) {
    t = (float)i / (float)steps;
    float h = Texture2DSampleGrad(Scan,GetMaterialSharedSampler(ScanSampler,Material.Wrap_WorldGroupSettings),
                                  uv - t*travel,gx,gy).b;
    gap = 1 - h - t;
    if (gap <= 0 || i == steps) break;
    previous = t;
    previousGap = gap;
}
float hit = lerp(previous,t,saturate(previousGap / max(previousGap-gap,0.00001)));
float pdo = rayCm * hit;
#if PIXEL_DEPTH_OFFSET_MODE == PODM_LEGACY
pdo *= saturate(dot(-V,ResolvedView.ViewForward));
#endif
return float3(uv - travel*hit, pdo);
#endif
"""


def install(source):
    opts = json.loads((source / 'placement.json').read_text())
    fn = load(shared['FUNCTION'])
    assets.make_directory(folder)
    tc = u.TextureCompressionSettings
    slots = {
        'Color': (next(source.glob('*_4K_BaseColor.jpg')), True, tc.TC_DEFAULT, False),
        'Normal': (next(source.glob('*_4K_Normal.jpg')), False, tc.TC_NORMALMAP, opts['flip_green_for_ue']),
        'ARH': (source / 'T_ForestFloor_ARH.png', False, tc.TC_MASKS, False),
    }
    textures = {k: shared['texture'](f, 'T_ForestFloor_'+k, srgb, kind, flip, folder=folder)
                for k, (f, srgb, kind, flip) in slots.items()}
    nodes = list(ed.get_material_function_expressions(fn))
    make = lambda cls, x, y: ed.create_material_expression_in_function(fn, cls, x, y)
    trace = next((n for n in nodes if n.get_editor_property('desc') == trace_tag), None)
    if not trace:
        world = next(n for n in nodes if isinstance(n,u.MaterialExpressionWorldPosition))
        obj = make(u.MaterialExpressionTextureObject, -1900, -440)
        obj.set_editor_property('texture', textures['ARH'])
        obj.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        size = make(u.MaterialExpressionConstant, -1890, -250)
        size.set_editor_property('r', opts['tile_cm'])
        strength = make(u.MaterialExpressionScalarParameter,-1880,-90)
        strength.set_editor_property('parameter_name','ForestFloorReliefCm')
        strength.set_editor_property('default_value',opts['relief_cm'])
        strength.set_editor_property('slider_max',3.0)
        strength.set_editor_property('group','Forest Floor')
        view = make(u.MaterialExpressionCameraVectorWS, -1870, 280)
        distance = make(u.MaterialExpressionDistance, -1520, 450)
        camera = make(u.MaterialExpressionCameraPositionWS,-1870, 480)
        wire(camera,'',distance,'A')
        wire(world,'',distance,'B')
        trace = make(u.MaterialExpressionCustom,-1240,-310)
        trace.set_editor_property('desc',trace_tag)
        trace.set_editor_property('description','ForestFloorIntersection')
        trace.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        bindings = {'P':world, 'Tile':size, 'Scan':obj, 'V':view, 'DistanceCm':distance, 'ReliefCm':strength}
        pins = []
        for name in bindings:
            pin = u.CustomInput()
            pin.set_editor_property('input_name',name)
            pins.append(pin)
        trace.set_editor_property('inputs',pins)
        for name,node in bindings.items():
            wire(node,'',trace,name)

        def mask(selected,x,y):
            node = make(u.MaterialExpressionComponentMask,x,y)
            for k in ('r','g','b','a'):
                node.set_editor_property(k,k in selected)
            wire(trace,'',node,'')
            return node

        uv = mask('rg', -950,-320)
        height = mask('b', -920,-500)
        out = make(u.MaterialExpressionFunctionOutput, 330,-420)
        out.set_editor_property('output_name','Relief')
        out.set_editor_property('sort_priority',2)
        wire(height,'',out,str(ed.get_material_expression_input_names(out)[0]))
        # Keep the existing Grass / Verge output GUIDs, the painted mask, and its projection.
        for node in nodes:
            if isinstance(node,u.MaterialExpressionTextureSample):
                name = node.get_editor_property('texture').get_name()
                rename = {'T_WildGrass_Color':'Color','T_WildGrass_Normal':'Normal','T_WildGrass_AR':'ARH'}
                if name in rename:
                    node.set_editor_property('texture',textures[rename[name]])
                    node.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
                    wire(uv,'',node,'UVs')
        old_uv = next((n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and
                       str(n.get_editor_property('code')).startswith('return P.xy /')),None)
        if old_uv:
            ed.delete_material_expression_in_function(fn,old_uv)
    trace.set_editor_property('code',TRACE)
    normal = next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and
                  'normalize(float3(N.xy' in str(n.get_editor_property('code')))
    normal.set_editor_property('code','return normalize(float3(N.xy * %.3f, max(N.z,0.001)));' % opts['normal_strength'])
    ed.update_material_function(fn)
    save(fn)
    return fn, opts


def publish(source, batch):
    fn, opts = install(source)
    sample = shared['SAMPLE']
    road = load(shared['ROAD']+'/M_EastRoad_Sensei')
    edge = load(sample+'/M_ForestVillageFringe')
    for mat in (road,edge):
        shared['mesh_surface'](mat,fn)
        save(mat)
    captured = load(sample+'/MF_ForestVillageSurface')
    if not u.ForestVillageRegion.build_surface_function(load(sample+'/MI_ForestSamplePalette'),captured):
        raise RuntimeError('Cannot capture Sensei sample material')
    shared['connect_sample_verge'](captured)
    ed.update_material_function(captured)
    save(captured)
    land = load(shared['ROOT']+'/M_ForestPathRoadVerge')
    shared['landscape_relief'](land,fn)
    materials = [road,edge,land,load(sample+'/M_ForestVillageSurface'),load(sample+'/M_ForestVillageGateApron')]
    for mat in materials:
        errors = ed.recompile_material(mat)
        if errors:
            raise RuntimeError(mat.get_name()+' '+str(errors))
        ed.get_statistics(mat)
        save(mat)
    receipt = dict(opts, listing='dae56d09-862c-4f77-9e72-a41281c49633', textures=folder,
                   surface=fn.get_path_name(), materials=[m.get_path_name() for m in materials],
                   full_distance_m=3.5, fade_out_m=12)
    (batch/'published.json').write_text(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    publish(Path(os.environ['FPS_FOREST_FLOOR_SOURCE']),Path(os.environ['FPS_FOREST_FLOOR_BATCH']))
