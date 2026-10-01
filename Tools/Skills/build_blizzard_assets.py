"""Author only /Game/Skills/Blizzard, compile and save. No PIE/render/test.

Reuses owned ice-spike smoke atlas and the imported Fab ice surface maps.
After restoring these base assets, run build_blizzard_storm_cloud.py for the
current StormV2 cloud and spatial landing sound used by the runtime component.
Run with UnrealEditor-Cmd -run=pythonscript -unattended -NullRHI.
"""
import json,sys,shutil
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir());sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,TOOLS,ref,setdata,assignments,save,CREATED
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter,expression
DEST='/Game/Skills/Blizzard';SRC=ROOT/'SourceAssets/Blizzard20260930'
EAL=u.EditorAssetLibrary

def own(source,name):
    path=DEST+'/'+name
    obj=u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source,path)
    if not obj:raise RuntimeError('Missing Blizzard authoring source '+source)
    return obj

def material(name):
    path=DEST+'/'+name
    m=u.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(m)
    return m

def node(m,cls):return LIB.create_material_expression(m,cls)
def custom(m,code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',kind);pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for name,(expr,channel) in inputs.items():
        if not LIB.connect_material_expressions(expr,channel,n,name):raise RuntimeError('Cannot connect '+name)
    return n
def output(n,channel,prop):
    if not LIB.connect_material_property(n,channel,prop):raise RuntimeError('Cannot connect material output')
def finish_material(m):
    errors=LIB.recompile_material(m)
    if errors:raise RuntimeError(m.get_path_name()+' compile failed: '+str(errors))
    save(m)

def surfaces():
    snow=material('M_BlizzardSnow');snow.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    tint=custom(snow,'return float3(.76,.83,.86);',{},u.CustomMaterialOutputType.CMOT_FLOAT3)
    output(tint,'',u.MaterialProperty.MP_BASE_COLOR)
    for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,.91),(u.MaterialProperty.MP_SPECULAR,.12)]:output(custom(snow,'return '+str(value)+';',{}),'',prop)
    LIB.set_material_usage(snow,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);finish_material(snow)
    frost=material('M_BlizzardFrost');frost.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL);frost.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    uv=node(frost,u.MaterialExpressionTextureCoordinate)
    texture=node(frost,u.MaterialExpressionTextureSample);texture.set_editor_property('texture',u.load_asset('/Game/Skills/IceWall/FabIceV3/T_IceSurfaceColor'));texture.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    tiled=custom(frost,'return UV*3;',{'UV':(uv,'')},u.CustomMaterialOutputType.CMOT_FLOAT2)
    LIB.connect_material_expressions(tiled,'',texture,'Coordinates')
    fade=node(frost,u.MaterialExpressionScalarParameter);fade.set_editor_property('parameter_name','Fade');fade.set_editor_property('default_value',0)
    mask=custom(frost,'float2 p=(UV-.5)*2;float d=length(p);float edge=saturate((1-d)*7);return edge*edge*(3-2*edge)*(.32+dot(C,float3(.2126,.7152,.0722))*.50)*Fade;',{'UV':(uv,''),'C':(texture,'RGB'),'Fade':(fade,'')})
    color=custom(frost,'return lerp(float3(.63,.75,.80),float3(.85,.90,.92),saturate(dot(C,float3(.2126,.7152,.0722))));',{'C':(texture,'RGB')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    output(mask,'',u.MaterialProperty.MP_OPACITY);output(color,'',u.MaterialProperty.MP_BASE_COLOR)
    output(custom(frost,'return .82;',{}),'',u.MaterialProperty.MP_ROUGHNESS);finish_material(frost)
    # Inherited smoke surface is lit; zero emissive for grey storm clouds.
    cloud=own('/Game/Skills/IceSpike/FrostV2/MI_ColdMist','MI_BlizzardCloud')
    for key,value in [('Emissive Gain',0),('Opacity Gain',1.15),('Near Fade Distance',35),('Depth Fade Distance',35)]:LIB.set_material_instance_scalar_parameter_value(cloud,key,value)
    LIB.update_material_instance(cloud);save(cloud)
    return snow,cloud

def meshes(snow):
    for name,mat in [('SM_BlizzardHail',snow),('SM_BlizzardSpike',u.load_asset('/Game/Skills/IceWall/FabIceV3/M_IceWall'))]:
        task=u.AssetImportTask();task.filename=str(SRC/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
        options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.automated_import_should_detect_type=False;options.import_as_skeletal=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.static_mesh_import_data.combine_meshes=True;options.static_mesh_import_data.auto_generate_collision=False;options.static_mesh_import_data.convert_scene_unit=True;options.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options=options;TOOLS.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name)
        if not mesh:raise RuntimeError('Mesh import failed '+name)
        mesh.set_material(0,mat);save(mesh)

def particles(kind,cloud_material):
    s=own('/Game/Skills/IceSpike/FrostV2/NS_ColdMist','NS_Blizzard'+kind);en='RocketTrail'
    trim(s,en,{'EmitterUpdateScript':['EmitterState','SpawnRate'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:EAL.remove_metadata_tag(s,'Fireball.Assignments.'+en+'.'+script)
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(s,en),{'bLocalSpace':False,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
    snow=kind=='Snow';cloud=kind=='Cloud'
    mat=cloud_material if cloud else u.load_asset('/Game/Skills/IceSpike/FrostV2/M_FrostCrystalSoft' if snow else '/Game/Skills/IceSpike/FrostV2/MI_ColdMist')
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(s,en,renderer=0),{'Material':mat.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},'SubImageSize':{'X':1 if snow else 8,'Y':1 if snow else 8},'bSubImageBlend':not snow,'Alignment':'Unaligned','FacingMode':'FaceCamera','bCastShadows':False,'MotionVectorSetting':'Disable','CutoutTexture':None,'bUseMaterialCutoutTexture':False})
    for name,typ in [('SurfaceNormal',VEC3),('RadiusX',FLOAT),('RadiusY',FLOAT),('CloudHeight',FLOAT)]:user_parameter(s,name,typ)
    a='frac(float(Particles.UniqueID)*.61803398875)';b='frac(float(Particles.UniqueID)*.754877666)';c='frac(float(Particles.UniqueID)*.569840296)'
    radial=f'(User.Side*cos({a}*6.2831853)*User.RadiusX+User.Up*sin({a}*6.2831853)*User.RadiusY)*sqrt({b})'
    if cloud:
        rate='8';life=f'2.4+{c}*.8';height=f'User.CloudHeight+({c}-.5)*35';velocity='User.Wind*.12'
        size=f'float2(180,145)*(1+{c}*.5)';rgba='float4(.13,.15,.17,.42)'
    elif snow:
        rate='170';life=f'(User.CloudHeight+60)/160';height=f'User.CloudHeight*({c}*.25+.75)';velocity=f'-User.SurfaceNormal*(160+{b}*80)+User.Wind+User.Up*sin({a}*6.2831853)*22'
        size=f'float2(2.2,3.4)*(1+{b}*1.8)';rgba='float4(.88,.94,.97,.80)'
    else:
        rate='24';life=f'1.4+{c}*.8';height=f'14+{c}*28';velocity=f'User.Wind*.7+User.Up*({b}*2-1)*12+User.SurfaceNormal*4'
        size=f'float2(65,32)*(1+{b}*.65)';rgba='float4(.63,.76,.82,.22)'
    expression(s,en,'EmitterUpdateScript','SpawnRate','SpawnRate',rate+'*saturate(User.Strength)*(1-saturate(User.DetailReduction))')
    assignments(s,en,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,life),'Particles.Position':(POSITION,f'User.CurrentPosition+{radial}+User.SurfaceNormal*({height})'),'Particles.Velocity':(VEC3,velocity),'Particles.SpriteSize':(VEC2,size),'Particles.SpriteRotation':(FLOAT,f'{c}*360'),'Particles.Color':(COLOR,rgba),'Particles.SubImageIndex':(FLOAT,'0')})
    fade='saturate(Particles.NormalizedAge*6)*saturate((1-Particles.NormalizedAge)*4)'
    if snow:fade+='*saturate(dot(Particles.Position-User.CurrentPosition,User.SurfaceNormal)/20)'
    alpha=rgba.replace(')',f'*({fade}))')
    assignments(s,en,'ParticleUpdateScript',{'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),'Particles.SpriteSize':(VEC2,size+('*(1+Particles.NormalizedAge*.25)' if not snow else '')),'Particles.Color':(COLOR,alpha),'Particles.SubImageIndex':(FLOAT,'0' if snow else 'clamp(Particles.NormalizedAge*56,0,63)')})
    s.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-900,-900,-120),max=u.Vector(900,900,1300)));save(s)

def main():
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) for p in dirty):raise RuntimeError('Preserve unsaved Blizzard assets')
    EAL.make_directory(DEST);snow,cloud=surfaces();meshes(snow)
    for kind in ['Cloud','Snow','Mist']:particles(kind,cloud)
    icon=ROOT/'SourceAssets/IceSkillIcons20260930/blizzard_cold_steel.png'
    if not icon.is_file():raise RuntimeError('Restore the generated Cold Steel Blizzard icon from SourceAssets/IceSkillIcons20260930')
    target=ROOT/'Content/ColdSteelData/Skills/blizzard_cold_steel.png';target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(icon,target)
    out=ROOT/'Saved/BlizzardMigration';out.mkdir(parents=True,exist_ok=True)
    receipt={'saved_assets':CREATED,'icon_source':str(icon),'ice_material':'/Game/Skills/IceWall/FabIceV3/M_IceWall','fx_source':'/Game/Skills/IceSpike/FrostV2/NS_ColdMist','components_per_zone':3,'hail_instances_per_zone':48,'max_zones_per_player':4,'gameplay_tested':False}
    (out/'asset-authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('BLIZZARD_ASSETS_SAVED '+json.dumps(receipt))

if __name__=='__main__':main()
