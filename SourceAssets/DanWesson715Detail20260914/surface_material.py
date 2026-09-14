"""715 polished surfaces: full source structure, independently controlled finish."""
from pathlib import Path
import bpy

SOURCE = Path(__file__).parent.parent / 'DanWesson71520260913/Textures/T_DW715_Normal.png'
FINISH = {
    'Frame': dict(base=(.62, .64, .66), rough=.045),
    'Cylinder': dict(base=(.65, .665, .68), rough=.035),
    'Steel': dict(base=(.58, .60, .62), rough=.060),
}
PART_ROUGHNESS = {
    'DW715_BarrelShroud': .060,
    'DW715_DW_Hummer1': .105,
    'DW715_DW_Trigger0': .075,
    'DW715_FrameLatch': .090,
    'DW715_RearLatch': .085,
    'DW715_ExtractorRod': .070,
    'DW715_LoaderKnob': .115,
}

def author_material(group, part, structural):
    cfg = FINISH[group]
    rough_base = PART_ROUGHNESS.get(part, cfg['rough'])
    m = bpy.data.materials.new('AUTH_DW715_Detail_' + part)
    m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    n.clear()
    out = n.new('ShaderNodeOutputMaterial')
    bs = n.new('ShaderNodeBsdfPrincipled')
    l.new(bs.outputs[0], out.inputs['Surface'])

    def math(kind, a, b=0):
        node = n.new('ShaderNodeMath'); node.operation = kind
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)): node.inputs[i].default_value = v
            else: l.new(v, node.inputs[i])
        return node.outputs[0]

    def saturate(v): return math('MINIMUM', math('MAXIMUM', v, 0), 1)

    geo = n.new('ShaderNodeNewGeometry')
    convex = saturate(math('MULTIPLY', math('SUBTRACT', geo.outputs['Pointiness'], .505), 22))
    cavity = saturate(math('MULTIPLY', math('SUBTRACT', .495, geo.outputs['Pointiness']), 18))
    rough = math('ADD', math('SUBTRACT', rough_base, math('MULTIPLY', convex, .009)), math('MULTIPLY', cavity, .085))
    line = None
    if structural:
        image = bpy.data.images.load(str(SOURCE), check_existing=True)
        image.colorspace_settings.name = 'Non-Color'
        uv = n.new('ShaderNodeUVMap'); uv.uv_map = 'SourceUV'
        tex = n.new('ShaderNodeTexImage'); tex.image = image
        l.new(uv.outputs[0], tex.inputs['Vector'])
        normal = n.new('ShaderNodeNormalMap'); normal.uv_map = 'SourceUV'
        normal.inputs['Strength'].default_value = 1.0
        l.new(tex.outputs['Color'], normal.inputs['Color'])
        l.new(normal.outputs[0], bs.inputs['Normal'])
        # This finite difference is a finish mask ONLY. The source normal above
        # is never filtered, reconstructed, desaturated or globally weakened.
        channels = {}
        for key, offset in {'L':(-1.5,0), 'R':(1.5,0), 'D':(0,-1.5), 'U':(0,1.5)}.items():
            add = n.new('ShaderNodeVectorMath'); add.operation = 'ADD'
            l.new(uv.outputs[0], add.inputs[0])
            add.inputs[1].default_value = (offset[0]/image.size[0], offset[1]/image.size[1], 0)
            sample = n.new('ShaderNodeTexImage'); sample.image = image
            l.new(add.outputs[0], sample.inputs['Vector'])
            split = n.new('ShaderNodeSeparateXYZ'); l.new(sample.outputs['Color'], split.inputs[0])
            channels[key] = split.outputs
        dx = math('ABSOLUTE', math('SUBTRACT', channels['R']['X'], channels['L']['X']))
        dy = math('ABSOLUTE', math('SUBTRACT', channels['U']['Y'], channels['D']['Y']))
        line = saturate(math('MULTIPLY', math('MAXIMUM', math('SUBTRACT', math('ADD', dx, dy), .015), 0), 6))
        rough = math('ADD', rough, math('MULTIPLY', line, .075))

    if group == 'Cylinder':
        # Preserve the mirror on the outer wall, with a restrained machined
        # finish on existing end faces. Author meshes use +Y as cylinder axis.
        split = n.new('ShaderNodeSeparateXYZ'); l.new(geo.outputs['Normal'], split.inputs[0])
        end = saturate(math('MULTIPLY', math('SUBTRACT', math('ABSOLUTE', split.outputs['Y']), .72), 3.57))
        rough = math('ADD', rough, math('MULTIPLY', end, .048))

    ao = n.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = .0010; ao.samples = 16; ao.only_local = True
    # Local creases remain separate from the albedo. Moving pieces are isolated
    # for baking, so no open-cylinder or reload shadow is painted onto the gun.
    occlusion = math('ADD', .45, math('MULTIPLY', ao.outputs['AO'], .55))
    tint = math('SUBTRACT', 1, math('MULTIPLY', cavity, .035))
    if line is not None: tint = math('MULTIPLY', tint, math('SUBTRACT', 1, math('MULTIPLY', line, .10)))
    base = n.new('ShaderNodeVectorMath'); base.operation = 'SCALE'
    base.inputs[0].default_value = cfg['base']; l.new(tint, base.inputs['Scale'])
    l.new(base.outputs[0], bs.inputs['Base Color']); l.new(rough, bs.inputs['Roughness'])
    bs.inputs['Metallic'].default_value = 1
    orm = n.new('ShaderNodeCombineColor'); orm.mode = 'RGB'
    l.new(occlusion, orm.inputs[0]); l.new(rough, orm.inputs[1]); orm.inputs[2].default_value = 1
    m['base_node'] = base.name; m['base_socket'] = base.outputs[0].name; m['orm_node'] = orm.name
    m['structure_strength'] = 1 if structural else 0; m['roughness_center'] = rough_base
    m['finish'] = 'Original structural normal; independent polished finish; no micro bump'
    return m
