"""Read the pre-repair soil patch in the visible village shader and the RVT writer."""
import unreal as u

MARKER='// Smith yard before restoration'
ROOT='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/SmeltingYard'

def bind(mat):
    lib=u.MaterialEditingLibrary
    nodes=list(lib.get_material_expressions(mat))
    work=[]
    for n in nodes:
        if not isinstance(n,u.MaterialExpressionCustom):
            continue
        source=n.get_editor_property('code')
        if MARKER in source:
            continue
        if str(n.get_editor_property('desc'))=='VillageTerrainRoad' and 'FVillageEdge edge;' in source:
            uv='uv'
            marker='FVillageEdge edge;'
            mask='mask'
        elif str(n.get_editor_property('desc'))=='VillageRoadEdge20261115' and 'float distance=(M.b-.5)*500.;' in source:
            uv='UV'
            marker='float distance=(yardMask.b-.5)*500.;'
            source=source.replace('M.b','yardMask.b').replace('M.g','yardMask.g')
            mask='yardMask'
        else:
            continue
        # The crop occupies texels [256,512) x [352,480) of the village's 2048 x 1024 mask.
        # Its alpha covers only the changed pixels. The rest of the village always reads the live mask.
        blend=f'''{MARKER}
float2 yardUV=({uv}*float2(2048.,1024.)-float2(256.,352.))/float2(256.,128.);
float2 yardDX=ddx({uv})*8., yardDY=ddy({uv})*8.;
[branch] if (SmithYardRepaired < .5 && all(yardUV>=0.) && all(yardUV<=1.)) {{
    float4 prior=Texture2DSampleGrad(SmithBefore,GetMaterialSharedSampler(SmithBeforeSampler,Material.Clamp_WorldGroupSettings),yardUV,yardDX,yardDY);
    {mask}.gb=lerp({mask}.gb,prior.gb,prior.a);
}}
'''
        if mask=='yardMask':
            blend='float3 yardMask=M.rgb;\n'+blend
        work.append((n,source.replace(marker,blend+marker,1)))
    if not work:
        return False
    tex=u.load_asset(ROOT+'/T_SmithYardBefore')
    if not tex:
        raise RuntimeError('Missing original courtyard mask')
    mat.modify()
    obj=lib.create_material_expression(mat,u.MaterialExpressionTextureObject)
    obj.set_editor_property('texture',tex)
    obj.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    flag=lib.create_material_expression(mat,u.MaterialExpressionScalarParameter)
    flag.set_editor_property('parameter_name','SmithYardRepaired')
    flag.set_editor_property('default_value',0.)
    for node,code in work:
        pins=list(node.get_editor_property('inputs'))
        for name in ('SmithBefore','SmithYardRepaired'):
            pin=u.CustomInput()
            pin.set_editor_property('input_name',name)
            pins.append(pin)
        node.set_editor_property('inputs',pins)
        if not lib.connect_material_expressions(obj,'',node,'SmithBefore') or not lib.connect_material_expressions(flag,'',node,'SmithYardRepaired'):
            raise RuntimeError('Could not bind repair state on '+mat.get_name())
        node.set_editor_property('code',code)
    return True
