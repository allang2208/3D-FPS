"""Continuous, axis-preserving scan coordinates shared by the terrain and dry RVT."""
import re

MARKER = '// Village scan spacing R2'


def warp(position, gradients=False):
    # Each coordinate remains monotone. There are no tile switches, mirrored
    # tangent frames or discontinuous derivatives at street and cell edges.
    phase = (f'float4 p = {position}.xyxy*float4(.0029,.0023,.0051,.0047)'
             '+float4(.73,-.91,2.07,.46);')
    if gradients:
        waves = ('float4 s, c; sincos(p,s,c);\n'
                 'float2 rate = 1.+c.xy*float2(.2378,.2116)+c.zw*float2(.1479,.1504);\n')
    else:
        waves = 'float4 s=sin(p);\n'
    return (MARKER+'\n'+phase+'\n'+waves+
            f'float2 bent = {position} + s.xy*float2(82.,92.) + s.zw*float2(29.,32.);\n')


def visible(code):
    if MARKER in code:
        return code
    line = 'float2 soilUV = (local+span*.5)'
    if code.count(line)!=1 or code.count('roadUV = (local+span*.5)')!=1:
        raise ValueError('Unknown visible village scan coordinates')
    code = code.replace(line,warp('local',True)+'float2 soilUV = (bent+span*.5)')
    code = code.replace('roadUV = (local+span*.5)', 'roadUV = (bent+span*.5)')
    # The mask stays in village plan coordinates. All seven PBR fetches use
    # the new scan coordinates and their analytic gradients for mip selection.
    code, count = re.subn(r'((?:roadUV|soilUV),)dx/([^,]+),dy/',r'\1(dx*rate)/\2,(dy*rate)/',code)
    if count!=7:
        raise ValueError(f'Expected seven village scan samples, found {count}')
    return code


def rvt_uv(span, tile):
    return warp('XY')+'return (bent+float2(%f,%f))/%f;'%(span[0]*.5,span[1]*.5,tile)


def update_saved_nodes(mat, plan):
    import unreal as u
    edit=u.MaterialEditingLibrary
    nodes=[node for node in edit.get_material_expressions(mat) if isinstance(node,u.MaterialExpressionCustom)]
    ex,ey=plan['surface_extent_m']
    span=(ex*200.,ey*200.)
    jobs=[]
    def match(predicate, transform):
        found=[n for n in nodes if predicate(n)]
        if len(found)!=1:
            raise ValueError(f'{mat.get_name()}: expected one scan node, found {len(found)}')
        source=found[0].get_editor_property('code')
        updated=transform(source)
        if source!=updated:
            jobs.append((found[0],updated))
    match(lambda n:n.get_editor_property('desc')=='VillageTerrainRoad',visible)
    for tile in (320.,plan['ground_dressing']['earth_tile_m']*100.):
        old='return (XY+float2(%f,%f))/%f;'%(span[0]*.5,span[1]*.5,tile)
        new=rvt_uv(span,tile)
        match(lambda n:n.get_editor_property('code') in (old,new),lambda _:new)
    if jobs:
        mat.modify()
        for node,code in jobs:
            node.set_editor_property('code',code)
    return bool(jobs)
