"""Publish the Wild Grass surface on hill grass and the existing forest path verge."""
import json
import os
from pathlib import Path

import unreal as u

ED = u.MaterialEditingLibrary
ASSETS = u.EditorAssetLibrary
ROOT = '/Game/ForestPathStudy/VillageRegion/WildGrass'
FUNCTION = ROOT + '/MF_HillsWildGrass'
ROAD = '/Game/WorldGeneration/TemperateHills/EastRiverRoad'
SAMPLE = '/Game/ForestPathStudy/VillageRegion/SurfaceSample'
STUDY = '/Game/ForestPathStudy/Materials/MI_ForestPathForest'
GRASS_TAG = 'R4 wild grass surface'
MOSS_TAG = 'R4 existing damp moss patches'
MOSS_FUNCTION = '/Game/ForestPathStudy/VillageRegion/ForestFloor/MF_NordicMossWorldMeters'
MOSS_UV_PER_METER = 0.5


def load(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing '+path)
    return obj


def save(obj):
    if not ASSETS.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+obj.get_path_name())


def wire(src, output, dest, pin):
    if not ED.connect_material_expressions(src,output,dest,pin):
        raise RuntimeError(f'{src.get_name()}.{output} -> {dest.get_name()}.{pin}')


def inputs(mat,node):
    return dict(zip(map(str,ED.get_material_expression_input_names(node)),ED.get_inputs_for_material_expression(mat,node)))


def bind_moss_projection(mat):
    if not ASSETS.does_asset_exist(MOSS_FUNCTION):
        return False
    fn=load(MOSS_FUNCTION)
    for call in ED.get_material_expressions(mat):
        if not isinstance(call,u.MaterialExpressionMaterialFunctionCall):
            continue
        pins=inputs(mat,call)
        size=pins.get('Size')
        if not isinstance(size,u.MaterialExpressionScalarParameter) or str(size.get_editor_property('parameter_name'))!='Size A':
            continue
        if call.get_editor_property('material_function')!=fn and not call.set_material_function(fn):
            raise RuntimeError('Could not bind the Nordic Moss projection on '+mat.get_name())
        size.set_editor_property('default_value',MOSS_UV_PER_METER)
        return True
    raise RuntimeError('Cannot find the Sensei A surface on '+mat.get_name())


def texture(file,name,srgb,compression,flip=False,clamp=False,folder=ROOT):
    path=folder+'/'+name
    if not ASSETS.does_asset_exist(path):
        task=u.AssetImportTask()
        task.filename=str(file)
        task.destination_path=folder
        task.destination_name=name
        task.automated=True
        task.save=False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    obj=load(path)
    obj.set_editor_property('srgb',srgb)
    obj.set_editor_property('compression_settings',compression)
    if compression==u.TextureCompressionSettings.TC_NORMALMAP:
        obj.set_editor_property('flip_green_channel',flip)
    if clamp:
        obj.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
        obj.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    save(obj)
    return obj


def surface(source):
    if ASSETS.does_asset_exist(FUNCTION):
        return load(FUNCTION)
    ASSETS.make_directory(ROOT)
    recipe=json.loads((source/'placement.json').read_text())
    T=u.TextureCompressionSettings
    color=texture(next(source.glob('*_4K_BaseColor.jpg')),'T_WildGrass_Color',True,T.TC_DEFAULT)
    normal=texture(next(source.glob('*_4K_Normal.jpg')),'T_WildGrass_Normal',False,T.TC_NORMALMAP,recipe['flip_green_for_ue'])
    rough=texture(source/'T_WildGrass_AR.png','T_WildGrass_AR',False,T.TC_MASKS)
    mask=texture(source/'T_RoadsideMask.png','T_ForestPathVerge',False,T.TC_MASKS,clamp=True)
    fn=u.AssetToolsHelpers.get_asset_tools().create_asset('MF_HillsWildGrass',ROOT,u.MaterialFunction,u.MaterialFunctionFactoryNew())
    ED.delete_all_material_expressions_in_function(fn)
    def expr(cls,x,y):
        return ED.create_material_expression_in_function(fn,cls,x,y)
    def custom(code,kind,bindings,x,y):
        c=expr(u.MaterialExpressionCustom,x,y)
        c.set_editor_property('code',code)
        c.set_editor_property('output_type',kind)
        pins=[]
        for name in bindings:
            p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
        c.set_editor_property('inputs',pins)
        for pin,(n,out) in bindings.items(): wire(n,out,c,pin)
        return c
    def sample(tex,stype,coords,x,y):
        n=expr(u.MaterialExpressionTextureSample,x,y)
        n.set_editor_property('texture',tex)
        n.set_editor_property('sampler_type',stype)
        wire(coords,'',n,'UVs')
        return n
    world=expr(u.MaterialExpressionWorldPosition,-1200,0)
    ty=u.CustomMaterialOutputType
    uv=custom('return P.xy / %.1f;'%recipe['size_cm'],ty.CMOT_FLOAT2,{'P':(world,'')},-900,0)
    sampler=u.MaterialSamplerType
    base=sample(color,sampler.SAMPLERTYPE_COLOR,uv,-600,-200)
    n=sample(normal,sampler.SAMPLERTYPE_NORMAL,uv,-600,40)
    ar=sample(rough,sampler.SAMPLERTYPE_MASKS,uv,-600,280)
    soft=custom('return normalize(float3(N.xy * %.4f, max(N.z,0.001)));'%recipe['normal_strength'],
                ty.CMOT_FLOAT3,{'N':(n,'RGB')},-320,30)
    attributes=expr(u.MaterialExpressionMakeMaterialAttributes,0,0)
    pins={str(p).replace(' ','').lower():str(p) for p in ED.get_material_expression_input_names(attributes)}
    for node,out,key in ((base,'RGB','basecolor'),(soft,'','normal'),(ar,'G','roughness'),(ar,'R','ambientocclusion')):
        wire(node,out,attributes,pins[key])
    ox,oy=recipe['mask_origin_cm']; sx,sy=recipe['mask_span_cm']
    mu=custom('return (P.xy-float2(%.1f,%.1f))/float2(%.1f,%.1f);'%(ox,oy,sx,sy),ty.CMOT_FLOAT2,{'P':(world,'')},-900,540)
    verge=sample(mask,sampler.SAMPLERTYPE_MASKS,mu,-600,540)
    for order,(title,node,pin) in enumerate((('Grass',attributes,''),('Verge',verge,'R'))):
        out=expr(u.MaterialExpressionFunctionOutput,330,order*420)
        out.set_editor_property('output_name',title)
        out.set_editor_property('sort_priority',order)
        wire(node,pin,out,str(ED.get_material_expression_input_names(out)[0]))
    ED.update_material_function(fn)
    save(fn)
    return fn


def grass_call(mat,fn):
    call=ED.create_material_expression(mat,u.MaterialExpressionMaterialFunctionCall,-2700,1600)
    if not call.set_material_function(fn):
        raise RuntimeError('Cannot use '+fn.get_name())
    call.set_editor_property('desc',GRASS_TAG)
    return call


def has_relief(fn):
    return any(isinstance(n,u.MaterialExpressionFunctionOutput) and
               str(n.get_editor_property('output_name'))=='Relief'
               for n in ED.get_material_function_expressions(fn))


def mesh_relief(mat,fn,call,verge,depth):
    if not has_relief(fn):
        return
    nodes=ED.get_material_expressions(mat)
    tag='Forest floor weighted pixel depth'
    if any(n.get_editor_property('desc')==tag for n in nodes):
        return
    dirt=next(n for n in nodes if isinstance(n,u.MaterialExpressionBlendMaterialAttributes)
              and inputs(mat,n)['A']==verge)
    make=next(n for n in nodes if isinstance(n,u.MaterialExpressionMakeMaterialAttributes)
              and inputs(mat,n).get('PixelDepthOffset')==depth)
    combine=ED.create_material_expression(mat,u.MaterialExpressionCustom,-500,2850)
    combine.set_editor_property('desc',tag)
    combine.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    combine.set_editor_property('code','return OldDepth + FloorDepth*(1-saturate(Moss))*(1-saturate(Dirt));')
    bindings={'OldDepth':(depth,''),'FloorDepth':(call,'Relief'),
              'Moss':(inputs(mat,verge)['Alpha'],''),'Dirt':(inputs(mat,dirt)['Alpha'],'')}
    pins=[]
    for name in bindings:
        pin=u.CustomInput()
        pin.set_editor_property('input_name',name)
        pins.append(pin)
    combine.set_editor_property('inputs',pins)
    for name,(node,out) in bindings.items():
        wire(node,out,combine,name)
    wire(combine,'',make,'PixelDepthOffset')


def landscape_relief(master,fn):
    if not has_relief(fn):
        return
    nodes=ED.get_material_expressions(master)
    tag='Forest floor painted relief'
    if any(n.get_editor_property('desc')==tag for n in nodes):
        return
    call=next(n for n in nodes if n.get_editor_property('desc')==GRASS_TAG)
    painted=next(n for n in nodes if isinstance(n,u.MaterialExpressionLandscapeLayerBlend))
    result=ED.get_material_property_input_node(master,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
    if inputs(master,result)['PixelDepthOffset']:
        raise RuntimeError('Landscape already has a separate pixel depth connection')
    # Copy the exact sensei height-blend inputs, including their output channels.
    # Only substitute scalar depth for the material attributes on each painted layer.
    weights=ED.create_material_expression(master,u.MaterialExpressionLandscapeLayerBlend,-400,2400)
    weights.set_editor_property('layers',painted.get_editor_property('layers'))
    weights.set_editor_property('desc',tag)
    relief=ED.create_material_expression(master,u.MaterialExpressionMultiply,-700,2400)
    wire(call,'Verge',relief,'A')
    wire(call,'Relief',relief,'B')
    zero=ED.create_material_expression(master,u.MaterialExpressionConstant,-700,2600)
    for pin in map(str,ED.get_material_expression_input_names(weights)):
        if pin.startswith('Layer '):
            wire(relief if pin in ('Layer AutoMaterial','Layer A') else zero,'',weights,pin)
    wire(weights,'',result,'PixelDepthOffset')


def mesh_surface(mat,fn,verge=None,depth=None):
    bind_moss_projection(mat)
    nodes=ED.get_material_expressions(mat)
    call=next((n for n in nodes if n.get_editor_property('desc')==GRASS_TAG),None)
    if verge is None:
        # Find the active moss/grass blend by its painted moss weight and A/B inputs.
        for n in nodes:
            if not isinstance(n,u.MaterialExpressionBlendMaterialAttributes): continue
            src=inputs(mat,n)
            a,b=src['A'],src['B']
            if b and b.get_name()=='MaterialExpressionReroute_8' and a and (
                a.get_name()=='MaterialExpressionReroute_7' or a==call):
                verge=n
                break
    if not verge: raise RuntimeError('Cannot identify painted grass on '+mat.get_name())
    if depth is None:
        depth=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and
                   'Sub-centimetre road relief' in str(n.get_editor_property('description')))
    previous=inputs(mat,verge)
    if previous['A']==call and call and previous['Alpha'].get_editor_property('desc')==MOSS_TAG:
        mesh_relief(mat,fn,call,verge,depth)
        return
    call=call or grass_call(mat,fn)
    moss=ED.create_material_expression(mat,u.MaterialExpressionCustom,-2200,1850)
    moss.set_editor_property('desc',MOSS_TAG)
    moss.set_editor_property('description','Retain concentrated damp moss')
    moss.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    moss.set_editor_property('code','return smoothstep(0.55, 0.94, M) * (1.0 - 0.96 * V);')
    pins=[]
    for name in ('M','V'):
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    moss.set_editor_property('inputs',pins)
    zero=ED.create_material_expression(mat,u.MaterialExpressionConstant,-2550,2000)
    wire(previous['Alpha'],'',moss,'M')
    wire(zero,'',moss,'V')
    wire(call,'Grass',verge,'A')
    wire(moss,'',verge,'Alpha')
    # Fully painted dirt keeps the original C height. Pure grass contributes zero PDO.
    depth.set_editor_property('code','float h=lerp(lerp(1.0,M,saturate(G)),D,saturate(W.x)); return (1-saturate(h))*0.8*(1-smoothstep(350,1200,Z));')
    wire(moss,'',depth,'G')
    mesh_relief(mat,fn,call,verge,depth)


def connect_sample_verge(fn):
    nodes=ED.get_material_function_expressions(fn)
    call=next(n for n in nodes if n.get_editor_property('desc')==GRASS_TAG)
    moss=next(n for n in nodes if n.get_editor_property('desc')==MOSS_TAG)
    wire(call,'Verge',moss,'V')


def landscape(fn):
    path=ROOT+'/M_ForestPathRoadVerge'
    master=load(path) if ASSETS.does_asset_exist(path) else ASSETS.duplicate_asset('/Game/Landscape/Materials/M_Landscape_Height',path)
    nodes=ED.get_material_expressions(master)
    if not any(n.get_editor_property('desc')==GRASS_TAG for n in nodes):
        layer=next(n for n in nodes if isinstance(n,u.MaterialExpressionLandscapeLayerBlend))
        current=inputs(master,layer)
        call=grass_call(master,fn)
        for y,key in enumerate(('Layer AutoMaterial','Layer A')):
            blend=ED.create_material_expression(master,u.MaterialExpressionBlendMaterialAttributes,-2000,1700+y*230)
            wire(current[key],'',blend,'A')
            wire(call,'Grass',blend,'B')
            wire(call,'Verge',blend,'Alpha')
            wire(blend,'',layer,key)
    landscape_relief(master,fn)
    moss_in_meters=bind_moss_projection(master)
    save(master)
    inst=load(STUDY)
    ED.set_material_instance_parent(inst,master)
    if moss_in_meters:
        ED.set_material_instance_scalar_parameter_value(inst,'Size A',MOSS_UV_PER_METER)
    ED.update_material_instance(inst)
    save(inst)
    return master


def publish():
    source=Path(os.environ['FPS_WILD_GRASS_SOURCE'])
    fn=surface(source)
    road=load(ROAD+'/M_EastRoad_Sensei')
    edge=load(SAMPLE+'/M_ForestVillageFringe')
    for mat in (road,edge):
        mesh_surface(mat,fn)
        save(mat)
    captured=load(SAMPLE+'/MF_ForestVillageSurface')
    if not u.ForestVillageRegion.build_surface_function(load(SAMPLE+'/MI_ForestSamplePalette'),captured):
        raise RuntimeError('Could not rebuild the calibrated forest surface')
    connect_sample_verge(captured)
    ED.update_material_function(captured)
    save(captured)
    land=landscape(fn)
    return (road,edge,land,load(SAMPLE+'/M_ForestVillageSurface'),load(SAMPLE+'/M_ForestVillageGateApron'))


if __name__=='__main__':
    mats=publish()
    for mat in mats:
        errors=ED.recompile_material(mat)
        if errors: raise RuntimeError(mat.get_name()+' '+str(errors))
        ED.get_statistics(mat)  # Finish the production shader build before saving.
        save(mat)
    p=Path(os.environ['FPS_GRASS_BATCH'])
    (p/'published.json').write_text(json.dumps({'listing':'0d62cc63-d6e9-45ef-b5d8-0dfaf4d9d027',
        'scan_id':'oilox20','surface':FUNCTION,'world_tile_cm':200,'normal_strength':0.28,
        'grass_pdo_cm':0,'materials':[m.get_path_name() for m in mats]},indent=2))
