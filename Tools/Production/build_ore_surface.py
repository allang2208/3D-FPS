"""Author mineral-specific veins over shared rock and forest-floor surfaces."""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/OreSurfaceHabitat20261110'
DEST='/Game/WorldGeneration/TemperateHills/OreRocks'
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
MINERALS={
    'Iron':dict(color=(.30,.13,.065),weather=(.12,.065,.035),metal=.55,rough=.50,width=.11,weathering=.55),
    'Copper':dict(color=(.72,.30,.12),weather=(.045,.18,.12),metal=.88,rough=.32,width=.105,weathering=.70),
    'Silver':dict(color=(.64,.71,.78),weather=(.065,.075,.09),metal=.96,rough=.27,width=.085,weathering=.48),
    'Gold':dict(color=(.86,.58,.17),weather=(.21,.14,.065),metal=.97,rough=.28,width=.065,weathering=.16),
}
REPORT={'saved':[],'minerals':MINERALS,'map_modified':False,'game_run':False,'visual_tested':False}

def backup(path):
    relative=path.split('.')[0].removeprefix('/Game/')
    for ext in ('.uasset','.uexp','.ubulk'):
        src=PROJECT/'Content'/(relative+ext);dst=ROOT/'Backups/Content'/(relative+ext)
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

def load(path):
    obj=u.load_asset(path)
    if obj is None:raise RuntimeError('Missing ore surface input: '+path)
    return obj

def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())

def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n

def wire(source,target,pin=''):
    obj,out=source if isinstance(source,tuple) else (source,'')
    if not L.connect_material_expressions(obj,out,target,pin):raise RuntimeError('Cannot connect '+pin)

def output(source,prop):
    obj,out=source if isinstance(source,tuple) else (source,'')
    if not L.connect_material_property(obj,out,getattr(u.MaterialProperty,'MP_'+prop)):
        raise RuntimeError('Cannot connect '+prop)

def custom(mat,code,inputs,dim,desc):
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    n=node(mat,u.MaterialExpressionCustom,code=code,inputs=pins,
        output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(dim)),desc=desc)
    for key,value in inputs.items():wire(value,n,key)
    return n

def scalar(mat,name,value):
    return node(mat,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)

def vector(mat,name,value):
    return node(mat,u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value,1))

def texture(mat,path,uv,normal=False):
    tex=load(path)
    sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else (
        u.MaterialSamplerType.SAMPLERTYPE_MASKS if tex.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_MASKS
        else u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    n=node(mat,u.MaterialExpressionTextureSample,texture=tex,sampler_type=sampler)
    wire(uv,n,'UVs')
    return (n,'RGB')

def build_materials():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Do not author during PIE')
    dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
    if dirty:raise RuntimeError('Preserve unsaved ore packages: '+repr(dirty))
    path=DEST+'/M_HillsOreRock';backup(path)
    mat=load(path)
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('use_material_attributes',False)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('used_with_nanite',True)
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    mat.set_editor_property('tangent_space_normal',True)
    world=node(mat,u.MaterialExpressionWorldPosition,
        world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    geom=node(mat,u.MaterialExpressionVertexNormalWS)
    local=node(mat,u.MaterialExpressionTransformPosition,
        transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
        transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
    wire(world,local)
    height=custom(mat,'return saturate((P.z-Low)/max(Span,1.0));',
        {'P':local,'Low':scalar(mat,'SourceMinZ',-278.591934),'Span':scalar(mat,'SourceHeightCm',537.999268)},1,'OreContactHeight')
    weights=custom(mat,'float3 w=pow(abs(N),4.0); return w/max(w.x+w.y+w.z,.0001);',{'N':geom},3,'OreProjectionWeights')
    uvs=[]
    for code in ('float2(P.y*(N.x<0?-1:1),P.z)','float2(-P.x*(N.y<0?-1:1),P.z)','float2(P.x*(N.z<0?-1:1),P.y)'):
        uvs.append(custom(mat,'return '+code+'*.009;',{'P':world,'N':geom},2,'OreWorldProjection'))
    base='/Game/UnrealNormandy/Textures/T_CliffSurface_03A_'
    def projected(suffix,normal=False):
        taps=[texture(mat,base+suffix,uv,normal) for uv in uvs]
        if normal:return taps
        return custom(mat,'return X*W.x+Y*W.y+Z*W.z;',dict(zip(('X','Y','Z','W'),taps+[weights])),3,'OreProjected'+suffix)
    rock=projected('BaseColor');packed=projected('RHAOM');normals=projected('Normal',True)
    field_pos=custom(mat,'return P*.023;',{'P':world},3,'OreVeinFieldScale')
    field=node(mat,u.MaterialExpressionNoise,noise_function=u.NoiseFunction.NOISEFUNCTION_GRADIENT_ALU,
        levels=2,quality=1,output_min=0.0,output_max=1.0,turbulence=False)
    wire(field_pos,field,'World Position')
    grain=custom(mat,'return saturate(P.g*.75+P.r*.25);',{'P':packed},1,'OreMineralGrain')
    masks=custom(mat,'''
float d=abs(Field-.5);
float band=(1.0-smoothstep(Width,Width+.055,d))*smoothstep(.18,.52,Grain);
float flecks=smoothstep(.70,.90,Grain)*(1.0-smoothstep(Width+.05,Width+.20,d));
float vein=saturate(band+.32*flecks);
float halo=saturate((1.0-smoothstep(Width+.04,Width+.12,d))-vein)*.45;
float soil=(1.0-smoothstep(.10,.34+(Grain-.5)*.18,H))*.90;
float weathered=vein*Weathering*smoothstep(.32,.73,Grain+.12*Field);
return float4(vein*(1.0-soil*.85),halo*(1.0-soil),soil,weathered*(1.0-soil*.85));
''',{'Field':field,'Grain':grain,'Width':scalar(mat,'VeinWidth',.085),'Weathering':scalar(mat,'MineralWeathering',.48),'H':height},4,'OreVeinsWeatheringContact')
    litter_uv=custom(mat,'return P.xy/200.0+float2(.273,.619);',{'P':world},2,'OreLitterGroundProjection')
    litter=texture(mat,'/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Textures/T_ForestFloor_BaseColor',litter_uv)
    wet=node(mat,u.MaterialExpressionCollectionParameter,
        collection=load('/Game/Weather/Materials/MPC_FPS_Weather'),parameter_name='WeatherWetness')
    color=custom(mat,'''
float weather=saturate(M.a/max(M.r,.001));
float3 host=Rock*.86;
float3 quartz=float3(.52,.49,.43)*(.75+.25*Grain);
host=lerp(host,quartz,M.g);
float3 mineral=lerp(Ore.rgb,Weather.rgb,weather)*(.72+.28*Grain);
float3 base=lerp(host,mineral,M.r);
float3 earth=Litter*.86;
base=lerp(base,earth,M.b);
return base*lerp(1.0,.72,saturate(Wet)*(1.0-.65*M.r));
''',{'Rock':rock,'Grain':grain,'M':masks,'Ore':vector(mat,'OreColor',(.64,.71,.78)),
        'Weather':vector(mat,'WeatheredColor',(.065,.075,.09)),'Litter':litter,'Wet':wet},3,'OreSurfaceColor')
    output(color,'BASE_COLOR')
    metal=custom(mat,'return saturate(M.r*Metal-M.a*.90)*(1.0-M.b);',
        {'M':masks,'Metal':scalar(mat,'OreMetallic',.96)},1,'OreMetalOnlyInVeins')
    output(metal,'METALLIC')
    rough=custom(mat,'''
float weather=saturate(M.a/max(M.r,.001));
float host=clamp(P.r*.85+.12,.48,.96);
float mineral=clamp(Rough+.18*(1.0-Grain)+.25*weather,.22,.86);
float value=lerp(lerp(host,mineral,M.r),.91,M.b);
return lerp(value,max(.24,value*.65),saturate(Wet));
''',{'P':packed,'M':masks,'Grain':grain,'Rough':scalar(mat,'OreRoughness',.27),'Wet':wet},1,'OreRoughnessAndRain')
    output(rough,'ROUGHNESS')
    ao=custom(mat,'return clamp(P.b,.65,1.0)*lerp(1.0,.82,M.b);',{'P':packed,'M':masks},1,'OreContactAO')
    output(ao,'AMBIENT_OCCLUSION')
    world_normal=custom(mat,'''
float3 signs=float3(N.x<0?-1:1,N.y<0?-1:1,N.z<0?-1:1);
float2 x=X.xy/max(X.z,.3), y=Y.xy/max(Y.z,.3), z=Z.xy/max(Z.z,.3);
float3 detail=float3(0,x.x*signs.x,x.y)*W.x
    +float3(-y.x*signs.y,0,y.y)*W.y+float3(z.x*signs.z,z.y,0)*W.z;
return normalize(N+detail*.65*(1.0-.55*M.b));
''',dict(zip(('X','Y','Z','W','N','M'),normals+[weights,geom,masks])),3,'OreWorldNormal')
    tangent=node(mat,u.MaterialExpressionTransform,
        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    wire(world_normal,tangent);output(tangent,'NORMAL')
    output(node(mat,u.MaterialExpressionConstant,r=0),'EMISSIVE_COLOR')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Ore material compile: '+repr(errors))
    save(mat)
    for name,values in MINERALS.items():
        path=DEST+'/MI_HillsOre_'+name;backup(path)
        mi=u.load_asset(path) or A.create_asset('MI_HillsOre_'+name,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(mi,mat)
        for key,value in {'OreColor':values['color'],'WeatheredColor':values['weather']}.items():
            L.set_material_instance_vector_parameter_value(mi,key,u.LinearColor(*value,1))
        for key,value in {'OreMetallic':values['metal'],'OreRoughness':values['rough'],'VeinWidth':values['width'],
                          'MineralWeathering':values['weathering'],'VeinEmissive':0}.items():
            L.set_material_instance_scalar_parameter_value(mi,key,value)
        L.update_material_instance(mi);save(mi)
    REPORT['finished_at']=datetime.now().astimezone().isoformat()
    (ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
    (ROOT/'Receipts/materials.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    u.log('ORE_SURFACE_SAVED '+str(len(REPORT['saved'])))
    return REPORT

if __name__=='__main__':build_materials()
