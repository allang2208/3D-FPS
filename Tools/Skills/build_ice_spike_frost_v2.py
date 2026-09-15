"""Author FrostV2 ice materials, imported TRELLIS meshes, and continuous condensation.
Necessary asset/shader compilation only. Does not launch gameplay or render a scene.
"""
import json, sys, shutil
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir());SRC=ROOT/'SourceAssets/IceSpike5080_20260915';DEST='/Game/Skills/IceSpike/FrostV2'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,TOOLS,ref,setdata,put,assignments,save
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter,expression
from build_ice_spike_assets import custom,finish

def own(source,name):
    path=DEST+'/'+name
    return u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source,path)

def material(name):
    path=DEST+'/'+name
    m=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(m);return m

def mist():
    source=u.load_asset('/Game/NiagaraExamples/Materials/MI_SmokeWispy_8x8_Emissive')
    parent=own(source.get_editor_property('parent').get_path_name(),'M_ColdMist')
    # DepthFade reads scene depth, so velocity output must stay disabled in this shader.
    parent.set_editor_property('output_translucent_velocity',False)
    parent.set_editor_property('enable_responsive_aa',True)
    parent.set_editor_property('disable_depth_test',False)
    parent.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    LIB.set_material_usage(parent,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES);finish(parent)
    m=own(source.get_path_name(),'MI_ColdMist');LIB.set_material_instance_parent(m,parent)
    for key,value in [('Opacity Gain',.75),('Emissive Gain',.06),('Near Fade Distance',45),('Depth Fade Distance',9),('Opacity Clip Value',0),('SubUV Speed',.6)]:
        LIB.set_material_instance_scalar_parameter_value(m,key,value)
    for key in ['Use Material SubUV','Use Particle Alpha As Threshold']:
        LIB.set_material_instance_static_switch_parameter_value(m,key,False)
    LIB.set_material_usage_override(m,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES,True,True)
    LIB.update_material_instance(m);save(m)
    s=own('/Game/Skills/IceSpike/NS_IceMotes','NS_ColdMist');en='RocketTrail'
    trim(s,en,{'EmitterUpdateScript':['EmitterState','SpawnRate'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:u.EditorAssetLibrary.remove_metadata_tag(s,'Fireball.Assignments.'+en+'.'+script)
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(s,en),{'bLocalSpace':False,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(s,en,renderer=0),{'Material':m.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},'SubImageSize':{'X':8,'Y':8},'Alignment':'Unaligned','FacingMode':'FaceCamera','bSubImageBlend':True,'bCastShadows':False,'MotionVectorSetting':'Disable','CutoutTexture':None,'bUseMaterialCutoutTexture':False})
    for name,typ in [('Side',VEC3),('Up',VEC3),('Flight',FLOAT),('Strength',FLOAT),('ReleasePulse',FLOAT)]:user_parameter(s,name,typ)
    expression(s,en,'EmitterUpdateScript','SpawnRate','SpawnRate','saturate(User.Strength)*(18+User.Flight*65+User.ReleasePulse*90)')
    a='frac(float(Particles.UniqueID)*.61803398875)';b='frac(float(Particles.UniqueID)*.754877666)'
    theta=f'({b}*6.2831853)';rad=f'(User.Side*cos({theta})+User.Up*sin({theta}))'
    assignments(s,en,'ParticleSpawnScript',{
        'Particles.Lifetime':(FLOAT,f'lerp(.40+.26*{a},.10+.06*{a},User.Flight)'),
        'Particles.Position':(POSITION,f'lerp(User.PreviousPosition,User.CurrentPosition,{a})+User.FlightDirection*(-21+{a}*29)+{rad}*(3+{b}*3)'),
        'Particles.Velocity':(VEC3,f'{rad}*(6+{a}*8)+float3(0,0,-15)-User.FlightDirection*User.Flight*38'),
        'Particles.SpriteSize':(VEC2,f'float2(11,15)*(1+{b}*.5)'),
        'Particles.SpriteRotation':(FLOAT,f'{a}*360'),
        'Particles.Color':(COLOR,'float4(.60,.73,.79,.42)'),
        'Particles.SubImageIndex':(FLOAT,'0')})
    assignments(s,en,'ParticleUpdateScript',{
        'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
        'Particles.SpriteSize':(VEC2,f'float2(11,15)*(1+{b}*.5)*(1+Particles.NormalizedAge*.8)'),
        'Particles.Color':(COLOR,'float4(.60,.73,.79,.42*saturate(Particles.NormalizedAge*7)*pow(1-Particles.NormalizedAge,1.5))'),
        'Particles.SubImageIndex':(FLOAT,'clamp(Particles.NormalizedAge*56,0,63)')})
    s.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-600,-600,-600),max=u.Vector(600,600,600)));save(s)
    return s

def texture(filename,name,normal=False):
    task=u.AssetImportTask();task.filename=str(SRC/'Game'/filename);task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=True;TOOLS.import_asset_tasks([task])
    t=u.load_asset(DEST+'/'+name)
    if normal:
        t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        t.set_editor_property('srgb',False);t.set_editor_property('flip_green_channel',True)
    save(t);return t

def crystal_material():
    m=material('M_FrostCrystalSoft')
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    m.set_editor_property('enable_responsive_aa',True)
    m.set_editor_property('output_translucent_velocity',False)
    m.set_editor_property('disable_depth_test',False)
    m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    uv=LIB.create_material_expression(m,u.MaterialExpressionTextureCoordinate)
    color=LIB.create_material_expression(m,u.MaterialExpressionParticleColor)
    depth=LIB.create_material_expression(m,u.MaterialExpressionPixelDepth)
    mask=custom(m,'float2 p=(UV-.5)*2;float d=abs(p.x)+abs(p.y);return pow(saturate(1-d),1.35)*A*saturate((D-35)/25);',{'UV':(uv,''),'A':(color,'A'),'D':(depth,'')})
    fade=LIB.create_material_expression(m,u.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',5)
    LIB.connect_material_expressions(mask,'',fade,'InOpacity');LIB.connect_material_property(fade,'',u.MaterialProperty.MP_OPACITY)
    LIB.connect_material_property(color,'RGB',u.MaterialProperty.MP_BASE_COLOR)
    for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,.65),(u.MaterialProperty.MP_SPECULAR,.16)]:
        n=custom(m,'return '+str(value)+';',{});LIB.connect_material_property(n,'',prop)
    # Lit frost specks have no emissive output or light renderer.
    LIB.set_material_usage(m,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES);finish(m);return m

def crystals():
    m=crystal_material()
    s=own('/Game/Skills/IceSpike/NS_IceMotes','NS_FrostCrystals');en='RocketTrail'
    trim(s,en,{'EmitterUpdateScript':['EmitterState','SpawnRate'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:u.EditorAssetLibrary.remove_metadata_tag(s,'Fireball.Assignments.'+en+'.'+script)
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(s,en,renderer=0),{'Material':m.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},'bCastShadows':False,'MotionVectorSetting':'Disable','SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,'CutoutTexture':None,'bUseMaterialCutoutTexture':False})
    for name,typ in [('Flight',FLOAT),('Strength',FLOAT),('Side',VEC3),('Up',VEC3)]:user_parameter(s,name,typ)
    expression(s,en,'EmitterUpdateScript','SpawnRate','SpawnRate','User.Strength*lerp(2.2,25,User.Flight)')
    a='frac(float(Particles.UniqueID)*.61803398875)';b='frac(float(Particles.UniqueID)*.754877666)'
    # Niagara CPU VectorVM needs the Hermite polynomial expanded instead of smoothstep().
    fade_in='saturate(Particles.NormalizedAge*4)';fade_out='saturate((Particles.NormalizedAge-.5)*2)'
    alpha=f'.24*{fade_in}*{fade_in}*(3-2*{fade_in})*(1-{fade_out}*{fade_out}*(3-2*{fade_out}))'
    assignments(s,en,'ParticleSpawnScript',{
        'Particles.Lifetime':(FLOAT,f'lerp(.45+.20*{a},.18+.12*{a},User.Flight)'),
        'Particles.Position':(POSITION,f'lerp(User.PreviousPosition,User.CurrentPosition,{a})-User.FlightDirection*({a}*22)+User.Side*sin({b}*6.283)*5+User.Up*cos({b}*6.283)*5'),
        'Particles.Velocity':(VEC3,'float3(0,0,-16)-User.FlightDirection*User.Flight*24'),
        'Particles.SpriteSize':(VEC2,'float2(.55,1.1)'),
        'Particles.Color':(COLOR,'float4(.48,.61,.67,0)'),
        'Particles.SubImageIndex':(FLOAT,'0')})
    assignments(s,en,'ParticleUpdateScript',{
        'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
        'Particles.SpriteSize':(VEC2,'float2(.55,1.1)*(1-.2*Particles.NormalizedAge)'),
        'Particles.Color':(COLOR,f'float4(.48,.61,.67,{alpha})'),
        'Particles.SubImageIndex':(FLOAT,'0')})
    save(s)

def ice_material(name,shell,base_tex,normal_tex):
    m=material(name)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT if shell else u.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT if shell else u.MaterialShadingModel.MSM_SUBSURFACE)
    if shell:
        m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        m.set_editor_property('enable_responsive_aa',True);m.set_editor_property('output_translucent_velocity',True)
        m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        m.set_editor_property('two_sided',False)
    uv=LIB.create_material_expression(m,u.MaterialExpressionTextureCoordinate)
    base=LIB.create_material_expression(m,u.MaterialExpressionTextureSample);base.set_editor_property('texture',base_tex)
    normal=LIB.create_material_expression(m,u.MaterialExpressionTextureSample);normal.set_editor_property('texture',normal_tex);normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    LIB.connect_material_expressions(uv,'',base,'Coordinates');LIB.connect_material_expressions(uv,'',normal,'Coordinates')
    vertex=LIB.create_material_expression(m,u.MaterialExpressionVertexColor)
    crack_tex=LIB.create_material_expression(m,u.MaterialExpressionTextureObject);crack_tex.set_editor_property('texture',u.load_asset('/Game/Skills/IceSpike/T_IceCracks'))
    cam=LIB.create_material_expression(m,u.MaterialExpressionCameraVectorWS)
    ts=LIB.create_material_expression(m,u.MaterialExpressionTransform)
    ts.set_editor_property('transform_source_type',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD);ts.set_editor_property('transform_type',u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    LIB.connect_material_expressions(cam,'',ts,'')
    cracks=custom(m,'float2 p=normalize(V).xy*.014;return saturate(Texture2DSample(T,TSampler,UV*2.1).r*.6+Texture2DSample(T,TSampler,UV*2.1+p).g*.3+Texture2DSample(T,TSampler,UV*2.1+p*2).b*.16);',{'T':(crack_tex,''),'UV':(uv,''),'V':(ts,'')})
    frost=custom(m,'return saturate(pow(saturate(1-H),4)*.72+C*.36);',{'H':(vertex,'R'),'C':(cracks,'')})
    tint=custom(m,'return lerp(float3(.26,.47,.54),float3(.75,.84,.86),F)*lerp(.86,1.05,saturate(dot(B,float3(.333,.333,.333))));' if shell else 'return lerp(float3(.18,.34,.40),float3(.59,.73,.78),saturate(F*.8+C*.25))*lerp(.90,1.08,saturate(dot(B,float3(.333,.333,.333))));',{'F':(frost,''),'C':(cracks,''),'B':(base,'RGB')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    LIB.connect_material_property(tint,'',u.MaterialProperty.MP_BASE_COLOR)
    n=custom(m,'return normalize(lerp(float3(0,0,1),N,.35));',{'N':(normal,'RGB')},u.CustomMaterialOutputType.CMOT_FLOAT3);LIB.connect_material_property(n,'',u.MaterialProperty.MP_NORMAL)
    for prop,code in [(u.MaterialProperty.MP_ROUGHNESS,'return lerp(.19,.40,F);' if shell else 'return lerp(.27,.45,F);'),(u.MaterialProperty.MP_SPECULAR,'return .24;' if shell else 'return .30;'),(u.MaterialProperty.MP_OPACITY,'return lerp(.25,.84,F);' if shell else 'return .22;')]:
        n=custom(m,code,{'F':(frost,'')});LIB.connect_material_property(n,'',prop)
    if not shell:
        n=custom(m,'return float3(.40,.72,.82);',{},u.CustomMaterialOutputType.CMOT_FLOAT3);LIB.connect_material_property(n,'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
    # No screen-color sampling, refraction connection, or emissive ice glow.
    finish(m);return m

def soften_existing_light():
    out=SRC/'SoftLight20260915';out.mkdir(exist_ok=True)
    archive=ROOT/'trash/skills-magic-20260915/SourceAssets/IceSpike5080_20260915/SoftLight20260915';archive.mkdir(parents=True,exist_ok=True)
    before={}
    for name in ['M_IceHeart','M_IceShell','MI_ColdMist','NS_FrostCrystals']:
        disk=ROOT/'Content/Skills/IceSpike/FrostV2'/(name+'.uasset')
        backup=archive/('before-'+name+'.uasset')
        if not backup.exists():shutil.copy2(disk,backup)
        asset=u.load_asset(DEST+'/'+name)
        if isinstance(asset,u.Material):
            before[name]={'shading_model':str(asset.get_editor_property('shading_model')),'inputs':{}}
            for prop in [u.MaterialProperty.MP_EMISSIVE_COLOR,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_SPECULAR,u.MaterialProperty.MP_NORMAL]:
                n=LIB.get_material_property_input_node(asset,prop)
                before[name]['inputs'][str(prop)]=None if not n else (n.get_editor_property('code') if isinstance(n,u.MaterialExpressionCustom) else n.get_class().get_name())
        elif isinstance(asset,u.NiagaraSystem):
            before[name]=API.call_method('GetRendererData',(ref(asset,'RocketTrail',renderer=0),)).export_text()
        else:
            before[name]={'emissive_gain':LIB.get_material_instance_scalar_parameter_value(asset,'Emissive Gain')}
    mote=u.load_asset('/Game/Skills/IceSpike/M_IceMote')
    before['M_IceMote']={'shading_model':str(mote.get_editor_property('shading_model')),'emissive_node':str(LIB.get_material_property_input_node(mote,u.MaterialProperty.MP_EMISSIVE_COLOR))}
    snapshot=archive/'before-material-inputs.json'
    if not snapshot.exists():snapshot.write_text(json.dumps(before,indent=2,ensure_ascii=False),encoding='utf-8')
    for name,shell in [('M_IceHeart',False),('M_IceShell',True)]:
        mat=u.load_asset(DEST+'/'+name)
        values={u.MaterialProperty.MP_ROUGHNESS:'return lerp(.19,.40,F);' if shell else 'return lerp(.27,.45,F);',u.MaterialProperty.MP_SPECULAR:'return .24;' if shell else 'return .30;',u.MaterialProperty.MP_NORMAL:'return normalize(lerp(float3(0,0,1),N,.35));'}
        for prop,code in values.items():
            n=LIB.get_material_property_input_node(mat,prop)
            if not isinstance(n,u.MaterialExpressionCustom):raise RuntimeError('Ice shading authoring input changed: '+name+'/'+str(prop))
            n.set_editor_property('code',code)
        finish(mat)
    crystals()
    mist_mat=u.load_asset(DEST+'/MI_ColdMist');LIB.set_material_instance_scalar_parameter_value(mist_mat,'Emissive Gain',.06)
    LIB.update_material_instance(mist_mat);save(mist_mat)
    (out/'authoring.json').write_text(json.dumps({'changes':['non-emissive lit frost specks','smooth alpha fade-in/out','lower hover spawn rate','broader weaker body highlights','normal intensity .35','mist emissive gain .06'],'status':'authored and shader/Niagara compiled','game_tested':False,'root_cause_scope':'material/input evidence only; no in-game reproduction'},indent=2),encoding='utf-8')

def meshes():
    base=texture('Ice_BaseColor.png','T_IceBaseColor');normal=texture('Ice_Normal.png','T_IceNormal',True)
    heart=ice_material('M_IceHeart',False,base,normal);shell=ice_material('M_IceShell',True,base,normal)
    paths=[]
    for i in range(1,4):
        name=f'SM_IceSpike_{i:02d}';task=u.AssetImportTask();task.filename=str(SRC/'Game'/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=True
        options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.convert_scene_unit=True
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=options;TOOLS.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);mesh.set_material(0,shell);save(mesh);paths.append(mesh.get_path_name())
    (SRC/'engine-authoring.json').write_text(json.dumps({'meshes':paths,'heart':heart.get_path_name(),'shell':shell.get_path_name(),'cold_mist':DEST+'/NS_ColdMist','status':'imported and shader compiled; not game tested'},indent=2),encoding='utf-8')

if __name__=='__main__':
    if '-IceLightOnly' in u.SystemLibrary.get_command_line():soften_existing_light()
    else:
        mist();crystals()
        if '-IceMistOnly' not in u.SystemLibrary.get_command_line():meshes()
    u.log('ICE_FROST_V2_AUTHORED')
