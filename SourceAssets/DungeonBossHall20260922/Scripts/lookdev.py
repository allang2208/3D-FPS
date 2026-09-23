"""Bind source PBR for inspection; Boss overrides also drive the deferred UE importer."""
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT.parent

def recipes():
    base=ASSETS/'DungeonAtmosphereV2_20260921/Authored'
    result={k:dict(maps=v,metallic=0) for k,v in json.loads((base/'material-manifest.json').read_text()).items()}
    interior=json.loads((ASSETS/'DungeonRoomInteriors20260921/Authored/material-manifest.json').read_text())
    for k in ('GreenPaint','YellowPaint','Iron','Rubber'):result[k]=interior[k]
    for sub in ('NaturalPass','TilePolish'):
        for k,v in json.loads((base/sub/'material-manifest.json').read_text()).items():result['V2_'+k]=dict(maps=v,metallic=0)
    fracture=json.loads((ASSETS/'DungeonTileFracture20260922/Authored/material-manifest.json').read_text())
    result['V2_CeramicFractureCore']=dict(maps=fracture['channels'],metallic=0)
    for dest,src in dict(ServicePaint='GreenPaint',ServiceHardware='BareSteel',FractureConcrete='Concrete',PipeEnamel='GreenPaint',PipeInner='Iron',PipeCutSteel='BareSteel',BridgeDeck='Iron',V2_WallReliefFinish='V2_NaturalRepair',V2_WallReliefBed='V2_NaturalMortar').items():
        if src=='V2_NaturalMortar':
            data=json.loads((base/'NaturalPass/material-manifest.json').read_text())
            result[dest]=dict(maps=data['NaturalMortar'],metallic=0)
        else:result[dest]=dict(result[src])
    wall=json.loads((ASSETS/'DungeonWallRelief20260922/Authored/material-manifest.json').read_text())
    for key in ('V2_WallReliefFinish','V2_WallReliefBed'):
        result[key]=dict(maps={k:v for k,v in wall['channels'].items() if k in ('BaseColor','Normal','Surface')},metallic=0,normal_strength=.65)
    pipe=ASSETS/'DungeonCombatExpansion20260922/Authored/Textures'
    result['PipeEnamel']=dict(maps={k:str(pipe/('PipeEnamel_'+k+'.png')) for k in ('BaseColor','Normal','Surface')},surface_metallic=True,normal_strength=.45)
    for key,color,rough,metal in [('PipeInner',[.075,.088,.060],.26,.5),('PipeCutSteel',[.22,.25,.24],.31,.88),('BridgeDeck',[.085,.11,.097],.42,.48)]:
        result[key]=dict(color=color,roughness=rough,metallic=metal,maps={'Normal':str(pipe/'PipeEnamel_Normal.png')},normal_strength=.45)
    result['ServiceHardware']=dict(result['PipeCutSteel'])
    for k,warm in [('CoolGlass',False),('WarmGlass',True)]:
        result[k]=dict(color=[1,.61,.27] if warm else [.67,.81,1],roughness=.35,metallic=0,emission=5)
    local=ROOT/'Authored/polish-materials.json'
    if local.exists():result.update(json.loads(local.read_text())['materials'])
    return result

def bind():
    specs=recipes();bound=[]
    for mat in bpy.data.materials:
        key=mat.name.removeprefix('RS_').split('.')[0]
        if key not in specs:continue
        spec=specs[key];mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
        out=nodes.new('ShaderNodeOutputMaterial');shader=nodes.new('ShaderNodeBsdfPrincipled');links.new(shader.outputs['BSDF'],out.inputs['Surface'])
        shader.inputs['Base Color'].default_value=(*spec.get('color',[.2,.2,.2]),1)
        shader.inputs['Metallic'].default_value=spec.get('metallic',0)
        shader.inputs['Roughness'].default_value=spec.get('roughness',.65)
        if spec.get('emission'):
            shader.inputs['Emission Color'].default_value=(*spec['color'],1);shader.inputs['Emission Strength'].default_value=spec['emission']
        maps={}
        for channel,filename in spec.get('maps',{}).items():
            tex=nodes.new('ShaderNodeTexImage');tex.label=channel;tex.image=bpy.data.images.load(filename,check_existing=True)
            tex.image.colorspace_settings.name='sRGB' if channel in ('BaseColor','RustColor') else 'Non-Color'
            maps[channel]=tex
            if channel=='Normal':
                normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=spec.get('normal_strength',.65)
                links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
            elif channel in ('BaseColor','Roughness','Metallic'):
                links.new(tex.outputs['Color'],shader.inputs['Base Color' if channel=='BaseColor' else channel])
            elif channel=='Surface':
                sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],sep.inputs['Color'])
                links.new(sep.outputs['Red'],shader.inputs['Roughness'])
                if spec.get('surface_metallic'):links.new(sep.outputs['Green'],shader.inputs['Metallic'])
        # CORNER vertex colour: R = authored contact grime; G = polished metal edge exposure.
        if spec.get('vertex_wear'):
            attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='ServiceAge'
            sep=nodes.new('ShaderNodeSeparateColor');links.new(attr.outputs['Color'],sep.inputs['Color'])
            original=shader.inputs['Base Color'].links[0].from_socket
            mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[2].default_value=(.24,.21,.17,1)
            links.new(original,mix.inputs[1]);links.new(sep.outputs['Red'],mix.inputs[0]);links.new(mix.outputs[0],shader.inputs['Base Color'])
            edge=nodes.new('ShaderNodeMixRGB');edge.inputs[2].default_value=(.22,.24,.23,1)
            links.new(mix.outputs[0],edge.inputs[1]);links.new(sep.outputs['Green'],edge.inputs[0]);links.new(edge.outputs[0],shader.inputs['Base Color'])
            metal=nodes.new('ShaderNodeMath');metal.operation='MAXIMUM';metal.inputs[1].default_value=spec.get('metallic',0)
            if shader.inputs['Metallic'].links:links.new(shader.inputs['Metallic'].links[0].from_socket,metal.inputs[1])
            links.new(sep.outputs['Green'],metal.inputs[0]);links.new(metal.outputs[0],shader.inputs['Metallic'])
        if spec.get('vertex_wetness'):
            attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='ServiceAge'
            sep=nodes.new('ShaderNodeSeparateColor');links.new(attr.outputs['Color'],sep.inputs['Color'])
            base=shader.inputs['Base Color'].links[0].from_socket
            wet=nodes.new('ShaderNodeMixRGB');wet.blend_type='MULTIPLY';wet.inputs[2].default_value=(.48,.51,.46,1)
            links.new(base,wet.inputs[1]);links.new(sep.outputs['Blue'],wet.inputs[0]);links.new(wet.outputs[0],shader.inputs['Base Color'])
            rough=nodes.new('ShaderNodeMixRGB');rough.inputs[2].default_value=(.22,.22,.22,1)
            links.new(shader.inputs['Roughness'].links[0].from_socket,rough.inputs[1]);links.new(sep.outputs['Blue'],rough.inputs[0]);links.new(rough.outputs[0],shader.inputs['Roughness'])
        if spec.get('vertex_pipe_weather'):
            attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='ServiceAge'
            sep=nodes.new('ShaderNodeSeparateColor');links.new(attr.outputs['Color'],sep.inputs['Color'])
            mul=nodes.new('ShaderNodeMath');mul.operation='MULTIPLY'
            links.new(sep.outputs['Green'],mul.inputs[0]);links.new(maps['Weather'].outputs['Color'],mul.inputs[1])
            factor=nodes.new('ShaderNodeMath');factor.operation='MULTIPLY';factor.inputs[1].default_value=1.8;factor.use_clamp=True;links.new(mul.outputs[0],factor.inputs[0])
            def mix(a,b):
                n=nodes.new('ShaderNodeMixRGB');links.new(factor.outputs[0],n.inputs[0]);links.new(a,n.inputs[1])
                if isinstance(b,tuple):n.inputs[2].default_value=(*b,1)
                else:links.new(b,n.inputs[2])
                return n.outputs[0]
            base=mix(maps['BaseColor'].outputs['Color'],maps['RustColor'].outputs['Color'])
            dirt=nodes.new('ShaderNodeMixRGB');dirt.blend_type='MULTIPLY';dirt.inputs[2].default_value=(.26,.23,.19,1)
            links.new(sep.outputs['Red'],dirt.inputs[0]);links.new(base,dirt.inputs[1]);links.new(dirt.outputs[0],shader.inputs['Base Color'])
            links.new(mix(maps['Roughness'].outputs['Color'],(.91,.91,.91)),shader.inputs['Roughness'])
            links.new(mix(maps['Metallic'].outputs['Color'],(0,0,0)),shader.inputs['Metallic'])
            rust=nodes.new('ShaderNodeNormalMap');rust.inputs['Strength'].default_value=.65;links.new(maps['RustNormal'].outputs['Color'],rust.inputs['Color'])
            normal=mix(shader.inputs['Normal'].links[0].from_socket,rust.outputs['Normal'])
            norm=nodes.new('ShaderNodeVectorMath');norm.operation='NORMALIZE';links.new(normal,norm.inputs[0]);links.new(norm.outputs[0],shader.inputs['Normal'])
        mat['boss_source_recipe']=key;bound.append(key)
    return bound
