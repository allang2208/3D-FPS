"""Create CrystalV2 materials, native Jason skeletal shells, lens mesh and bounded condensation."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()));SRC=ROOT/'SourceAssets/IceArmor20261017/CrystalV2'
DEST='/Game/Skills/IceArmor20261017/CrystalV2';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
RECEIPT=SRC/'assets-saved.json'
saved=[]
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing authoring dependency: '+path)
    return asset
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    disk=ROOT/'Content'/(asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
    if not disk.is_file() or not disk.stat().st_size:raise RuntimeError('Missing saved file: '+str(disk))
    saved.append({'asset':asset.get_path_name(),'bytes':disk.stat().st_size})
    RECEIPT.write_text(json.dumps({'saved':saved,'gameplay_tested':False},indent=2),encoding='utf-8')

def material(name,lens=False,chip=False):
    m=u.load_asset(DEST+'/'+name) if E.does_asset_exist(DEST+'/'+name) else A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    # UE 5.8 DeleteAllMaterialExpressions iterates the collection it removes
    # from. Delete a snapshot so old parameters/disconnected nodes cannot survive.
    for previous in list(L.get_material_expressions(m)):L.delete_material_expression(m,previous)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    m.set_editor_property('disable_depth_test',lens);m.set_editor_property('two_sided',chip)
    m.set_editor_property('enable_responsive_aa',True);m.set_editor_property('output_translucent_velocity',True)
    m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_AFTER_DOF if lens else u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    m.set_editor_property('refraction_method',u.RefractionMode.RM_NONE if lens or chip else u.RefractionMode.RM_INDEX_OF_REFRACTION)
    if not lens and not chip:L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    if chip:L.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    def node(cls):return L.create_material_expression(m,cls)
    def wire(a,p,b,q):
        if not L.connect_material_expressions(a,p,b,q):raise RuntimeError(name+' input '+q)
    def out(n,p):
        if not L.connect_material_property(n,'',p):raise RuntimeError(name+' output '+str(p))
    def scalar(k,v):
        n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',k);n.set_editor_property('default_value',v);return n
    def vector(k,v):
        n=node(u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',k);n.set_editor_property('default_value',u.LinearColor(*v));return n
    def custom(code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
        n=node(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',kind)
        pins=[]
        for key in inputs:
            p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        n.set_editor_property('inputs',pins)
        for key,(expr,pin) in inputs.items():wire(expr,pin,n,key)
        return n
    uv=node(u.MaterialExpressionTextureCoordinate);uv1=node(u.MaterialExpressionTextureCoordinate);uv1.set_editor_property('coordinate_index',1)
    color=node(u.MaterialExpressionVertexColor);cam=node(u.MaterialExpressionCameraVectorWS)
    view=node(u.MaterialExpressionTransform);view.set_editor_property('transform_source_type',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD);view.set_editor_property('transform_type',u.MaterialVectorCoordTransform.TRANSFORM_TANGENT);wire(cam,'',view,'')
    world=node(u.MaterialExpressionWorldPosition)
    tex=node(u.MaterialExpressionTextureObject);tex.set_editor_property('texture',load('/Game/Skills/IceSpike/T_IceCracks'))
    cracks=custom('''float2 p=clamp(normalize(V).xy/max(abs(normalize(V).z),.35),-1.2,1.2)*.026;
float major=Texture2DSample(T,TSampler,UV*.93).r;
float middle=Texture2DSample(T,TSampler,UV*1.43+p).g;
float fine=Texture2DSample(T,TSampler,UV*4.21+p*2.2).b;
return saturate(major*.24+middle*.19+fine*.13);''',{'T':(tex,''),'UV':(uv,''),'V':(view,'')})
    grain=custom('''float2 q=UV*91;float2 c=floor(q);float h=frac(sin(dot(c,float2(127.1,311.7)))*43758.5453);
float bubble=(1-smoothstep(.045,.09,length(frac(q)-.5)))*step(.965,h);
return float2(frac(sin(dot(UV,float2(23.41,37.19)))*631.27),bubble);''',{'UV':(uv,'')},u.CustomMaterialOutputType.CMOT_FLOAT2)
    # Readable frosted bevels around a clear core, instead of uniformly dark glass.
    frost=custom('return saturate(smoothstep(.025,.38,Rim)*(.52+.32*G.x)+C*.34);',{'Rim':(color,'R'),'G':(grain,''),'C':(cracks,'')})
    facing=custom('return pow(1-saturate(abs(dot(normalize(N),normalize(V)))),3);',{'N':(node(u.MaterialExpressionVertexNormalWS),''),'V':(cam,'')})
    fade=scalar('Fade',1);growth=scalar('Growth',1);dissolve=scalar('Dissolve',0);pulse=scalar('Pulse',0);impact=scalar('Impact',0)
    hit=vector('HitPosition',(0,0,-10000,1))
    impact_mask=custom('return pow(saturate(1-distance(P,Hit.xyz)/32),2)*Impact;',{'P':(world,''),'Hit':(hit,''),'Impact':(impact,'')})
    coverage=custom('''float phase=saturate(Seed*.24+(1-UV.y)*.64);
float grow=smoothstep(phase-.09,phase+.12,saturate((Growth-.20)/.80));
float edge=max(0,smoothstep(phase-.10,phase+.10,min(1,Growth+.12))-grow);
float breakup=1-smoothstep(Noise.x*.38+.17,Noise.x*.38+.38,Dissolve);
return float2(grow*breakup*Fade,edge*breakup*Fade);''',{'Seed':(color,'B'),'UV':(uv1,''),'Growth':(growth,''),'Noise':(grain,''),'Dissolve':(dissolve,''),'Fade':(fade,'')},u.CustomMaterialOutputType.CMOT_FLOAT2)
    hide_back=scalar('HideBack',0);hide_thigh=scalar('HideThigh',0)
    visibility=custom('return (1-Back*step(.18,Zone)*step(Zone,.32))*(1-Thigh*step(.67,Zone)*step(Zone,.83));',{'Zone':(color,'G'),'Back':(hide_back,''),'Thigh':(hide_thigh,'')})
    surface=node(u.MaterialExpressionTextureSample);surface.set_editor_property('texture',load('/Game/Skills/IceWall/FabIceV3/T_IceSurfaceColor'));surface.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR);wire(uv,'',surface,'UVs')
    base=custom('float cloud=saturate(dot(S,float3(.2126,.7152,.0722)));float3 core=lerp(float3(.10,.25,.34),float3(.27,.46,.57),cloud);return lerp(core,float3(.67,.84,.91),saturate(F*.92+C*.20+G.y*.6));',{'F':(frost,''),'C':(cracks,''),'G':(grain,''),'S':(surface,'RGB')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    alpha=custom('return saturate(((Core+F*FrostOpacity+C*.18+G.y*.20+R*.14+H*.22)*Cov.x+F*.46*Cov.y)*Visible);',{'Core':(scalar('CoreOpacity',.30 if lens else (.55 if chip else .46)),''),'FrostOpacity':(scalar('FrostOpacity',.48 if lens else .55),''),'F':(frost,''),'C':(cracks,''),'G':(grain,''),'R':(facing,''),'H':(impact_mask,''),'Cov':(coverage,''),'Visible':(visibility,'')})
    if chip:
        age=node(u.MaterialExpressionPerInstanceCustomData);age.set_editor_property('data_index',0);age.set_editor_property('const_default_value',1.)
        interp=node(u.MaterialExpressionVertexInterpolator);wire(age,'',interp,str(L.get_material_expression_input_names(interp)[0]))
        alpha=custom('return A*Life;',{'A':(alpha,''),'Life':(interp,'')})
    normal=node(u.MaterialExpressionTextureSample);normal.set_editor_property('texture',load('/Game/Ice/Textures/T_Ice6_normal'));normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL);wire(uv,'',normal,'UVs')
    n=custom('return normalize(float3(N.xy*.21,N.z));',{'N':(normal,'RGB')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    rough=custom('return clamp(.075+F*.46+G.x*.035,.075,.36);',{'F':(frost,''),'G':(grain,'')})
    wave=custom('return P*(1-smoothstep(.08,.22,abs(UV.y-Phase)));',{'P':(pulse,''),'UV':(uv1,''),'Phase':(scalar('PulsePhase',0),'')})
    # Only the ice receives one exposure compensation; scene illumination is untouched.
    emission=custom('float steady=.025+F*.24+C*.12+R*.07;float energy=(steady+P*(F*.95+C*.8)+H*(C*2.0+.24))*Cov.x+Cov.y*F*.55;return float3(.26,.54,.70)*energy*Visibility/max(Exposure,.05);',{'F':(frost,''),'Cov':(coverage,''),'R':(facing,''),'P':(wave,''),'C':(cracks,''),'H':(impact_mask,''),'Visibility':(visibility,''),'Exposure':(node(u.MaterialExpressionEyeAdaptation),'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    for e,p in [(base,u.MaterialProperty.MP_BASE_COLOR),(n,u.MaterialProperty.MP_NORMAL),(rough,u.MaterialProperty.MP_ROUGHNESS),(alpha,u.MaterialProperty.MP_OPACITY),(emission,u.MaterialProperty.MP_EMISSIVE_COLOR),(scalar('Specular',.28),u.MaterialProperty.MP_SPECULAR)]:out(e,p)
    if not lens and not chip:out(scalar('IceRefraction',1.025),u.MaterialProperty.MP_REFRACTION)
    if lens:
        local=node(u.MaterialExpressionPreSkinnedPosition);centres=node(u.MaterialExpressionTextureCoordinate);centres.set_editor_property('coordinate_index',2)
        correction=custom('return Right.xyz*(P.y-Centre.x*100)*Amount;',{'Right':(vector('LensRight',(0,1,0,1)),''),'P':(local,''),'Centre':(centres,''),'Amount':(scalar('LensNarrowScale',0),'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
        out(correction,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError(name+': '+str(errors))
    save(m);return m

def geometry(name,mat,native,target):
    data=json.loads((SRC/(name+'.json')).read_text())
    buffers=u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*p) for p in data['positions']],normals=[u.Vector(*n) for n in data['normals']],
        uv0=[u.Vector2D(*v) for v in data['uv']],uv1=[u.Vector2D(*v) for v in data['uv1']],uv2=[u.Vector2D(*v) for v in data['uv2']],
        vertex_colors=[u.LinearColor(*c) for c in data['colors']],triangles=[u.IntVector(*t) for t in data['triangles']])
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,buffers,0,True)
    G=u.GeometryScript_AssetUtils;path=DEST+'/'+name
    existing=u.load_asset(path) if E.does_asset_exist(path) else None
    if data['skinned']:
        B=u.GeometryScript_BoneWeights;B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
        for vi,bindings in enumerate(data['weights']):B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=bi,weight=w) for bi,w in bindings])
        opts=u.GeometryScriptCreateNewSkeletalMeshAssetOptions();opts.use_mesh_bone_proportions=True;opts.enable_recompute_normals=False;opts.enable_recompute_tangents=True;opts.materials={'CrystalIce':mat}
        if existing:
            write=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[mat],new_material_slot_names=['CrystalIce'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
            _,status=G.copy_mesh_to_skeletal_mesh(dm,existing,write,u.GeometryScriptMeshWriteLOD());asset=existing
        else:asset,status=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,target.skeleton,path,opts)
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Skeletal shell creation failed: '+name)
        asset.set_editor_property('physics_asset',None);asset.set_editor_property('post_process_anim_blueprint',None)
        u.FPSModularOutfitComponent.configure_outfit_lods(asset)
        if not u.SkeletalMeshEditorSubsystem.regenerate_lod(asset,3,True,False):raise RuntimeError('Shell LOD build failed: '+name)
    else:
        if existing:
            _,status=G.copy_mesh_to_static_mesh(dm,existing,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD());asset=existing
        else:asset,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_collision=False))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Static crystal creation failed: '+name)
        asset.set_material(0,mat)
    save(asset)

def mist():
    sys.path.insert(0,str(ROOT/'Tools/Skills'))
    from build_fireball_assets import ref,setdata,assignments,save as save_niagara
    from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
    from build_fireball_flight import expression
    path=DEST+'/NS_IceArmor_Condensation'
    s=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Skills/IceSpike/FrostV2/NS_ColdMist',path)
    en='RocketTrail';trim(s,en,{'EmitterUpdateScript':['EmitterState','SpawnRate'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:E.remove_metadata_tag(s,'Fireball.Assignments.'+en+'.'+script)
    setdata('SetEmitterData',u.NiagaraExt_EmitterData,ref(s,en),{'bLocalSpace':False,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
    expression(s,en,'EmitterUpdateScript','SpawnRate','SpawnRate','saturate(User.Strength)*24')
    a='frac(float(Particles.UniqueID)*.61803398875)';b='frac(float(Particles.UniqueID)*.754877666)'
    radial=f'float3(cos({b}*6.2831853),sin({b}*6.2831853),0)'
    assignments(s,en,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,f'.42+{a}*.22'),'Particles.Position':(POSITION,f'User.CurrentPosition+{radial}*(22+{a}*8)+float3(0,0,-55+{a}*82)'),
        'Particles.Velocity':(VEC3,f'{radial}*8+User.Wind+float3(0,0,-12)'), 'Particles.SpriteSize':(VEC2,f'float2(12,16)*(1+{a}*.3)'),
        'Particles.SpriteRotation':(FLOAT,f'{a}*360'),'Particles.Color':(COLOR,'float4(.52,.68,.76,.20)'),'Particles.SubImageIndex':(FLOAT,'0')})
    assignments(s,en,'ParticleUpdateScript',{'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
        'Particles.SpriteSize':(VEC2,'Particles.SpriteSize*(1+Engine.DeltaTime*.65)'),
        'Particles.Color':(COLOR,'float4(.52,.68,.76,.20*saturate(Particles.NormalizedAge*8)*pow(1-Particles.NormalizedAge,1.7))'),
        'Particles.SubImageIndex':(FLOAT,'clamp(Particles.NormalizedAge*56,0,63)')})
    s.set_editor_property('fixed_bounds',u.Box(min=u.Vector(-110,-110,-110),max=u.Vector(110,110,125)))
    save_niagara(s);save(s)

def main():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('End PIE before CrystalV2 asset authoring')
    E.make_directory(DEST)
    world=material('M_IceArmor_World');lens=material('M_IceArmor_Lens',True);chip=material('M_IceArmor_Chip',False,True)
    target=load('/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body')
    native,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(target,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read Jason skeleton for ice shells')
    for part in ('Torso','Arms','Legs'):
        for profile in range(3):geometry(f'SK_IceArmor_{part}_{profile}',world,native,target)
    geometry('SM_IceArmor_Clusters',lens,native,target);geometry('SM_IceArmor_Chip',chip,native,target);mist()
    print('ICE_ARMOR_CRYSTAL_V2_SAVED '+str(len(saved)),flush=True)
if __name__=='__main__':main()
