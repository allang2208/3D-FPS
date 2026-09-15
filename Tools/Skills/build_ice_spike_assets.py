"""Author ice assets from owned meshes/VFX. No game, scene render or acceptance run.

Run with UnrealEditor-Cmd -run=pythonscript -AllowCommandletRendering -multiprocess.
"""
import json, sys
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir());DEST='/Game/Skills/IceSpike';SRC=ROOT/'SourceAssets/IceSpike20260915'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,TOOLS,ref,emitters,setdata,put,assignments,save
from build_fireball_flames import trim,FLOAT,VEC2,VEC3,POSITION,COLOR
from build_fireball_flight import user_parameter,expression

def custom(m,code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    n=LIB.create_material_expression(m,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',kind)
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for name,(node,out) in inputs.items():LIB.connect_material_expressions(node,out,n,name)
    return n

def material(name):
    m=u.load_asset(DEST+'/'+name) if u.EditorAssetLibrary.does_asset_exist(DEST+'/'+name) else TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(m);return m

def finish(m):
    errors=LIB.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    save(m)

def ice():
    m=material('M_IceSpike')
    # A lit solid interior avoids temporal transparency trails. Subsurface light,
    # layered crack sampling and glossy surface supply the ice depth cues.
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE)
    uv=LIB.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',1.7);uv.set_editor_property('v_tiling',1.3)
    texture=LIB.create_material_expression(m,u.MaterialExpressionTextureObject)
    texture.set_editor_property('texture',u.load_asset(DEST+'/T_IceCracks'))
    camera=LIB.create_material_expression(m,u.MaterialExpressionCameraVectorWS)
    ts=LIB.create_material_expression(m,u.MaterialExpressionTransform)
    ts.set_editor_property('transform_source_type',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
    ts.set_editor_property('transform_type',u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    LIB.connect_material_expressions(camera,'',ts,'')
    # Texture channels are sampled rather than screen color; no screen-refraction mosaic.
    cracks=custom(m,'float3 v=normalize(V);float2 p=v.xy/max(abs(v.z),.35)*.022;float a=Texture2DSample(Tex,TexSampler,UV).r;float b=Texture2DSample(Tex,TexSampler,UV+p).g;float c=Texture2DSample(Tex,TexSampler,UV+p*2.4).b;return saturate(a*.75+b*.45+c*.25);',{'Tex':(texture,''),'UV':(uv,''),'V':(ts,'')})
    normal=LIB.create_material_expression(m,u.MaterialExpressionPixelNormalWS)
    base=custom(m,'float edge=pow(1-saturate(abs(dot(normalize(N),normalize(V)))),2.5);return lerp(float3(.014,.075,.13),float3(.38,.65,.77),saturate(C*.65+edge*.3));',{'C':(cracks,''),'N':(normal,''),'V':(camera,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    LIB.connect_material_property(base,'',u.MaterialProperty.MP_BASE_COLOR)
    for prop,code in [(u.MaterialProperty.MP_ROUGHNESS,'return lerp(.12,.38,C);'),(u.MaterialProperty.MP_SPECULAR,'return .62;'),(u.MaterialProperty.MP_OPACITY,'return .30;')]:
        n=custom(m,code,{'C':(cracks,'')});LIB.connect_material_property(n,'',prop)
    sub=custom(m,'return float3(.12,.42,.56);',{},u.CustomMaterialOutputType.CMOT_FLOAT3);LIB.connect_material_property(sub,'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
    glow=custom(m,'return float3(.008,.025,.035)*C;',{'C':(cracks,'')},u.CustomMaterialOutputType.CMOT_FLOAT3);LIB.connect_material_property(glow,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    finish(m);return m

def trail():
    m=material('M_IceMote');m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('enable_responsive_aa',True);m.set_editor_property('output_translucent_velocity',True);m.set_editor_property('disable_depth_test',False)
    uv=LIB.create_material_expression(m,u.MaterialExpressionTextureCoordinate);color=LIB.create_material_expression(m,u.MaterialExpressionParticleColor)
    mask=custom(m,'float2 p=(UV-.5)*2;return saturate(1-abs(p.x)-abs(p.y))*Alpha;',{'UV':(uv,''),'Alpha':(color,'A')})
    LIB.connect_material_property(mask,'',u.MaterialProperty.MP_OPACITY);LIB.connect_material_property(color,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.set_material_usage(m,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES);finish(m)
    path=DEST+'/NS_IceMotes'
    s=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset('/Game/Skills/Fireball/NS_FireballVelocityTrail',path)
    en='RocketTrail'
    trim(s,en,{'EmitterUpdateScript':['EmitterState','SpawnRate'],'ParticleSpawnScript':['InitializeParticle'],'ParticleUpdateScript':['ParticleState']})
    for script in ['ParticleSpawnScript','ParticleUpdateScript']:u.EditorAssetLibrary.remove_metadata_tag(s,'Fireball.Assignments.'+en+'.'+script)
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(s,en,renderer=0),{'Material':m.get_path_name(),'SubImageSize':{'X':1,'Y':1},'Alignment':'Unaligned','FacingMode':'FaceCamera','bSubImageBlend':False,'MotionVectorSetting':'Precise','CutoutTexture':None,'bUseMaterialCutoutTexture':False})
    expression(s,en,'EmitterUpdateScript','SpawnRate','SpawnRate','clamp(User.FlightSpeed/60,0,45)')
    seed='frac(float(Particles.UniqueID)*.61803398875)'
    assignments(s,en,'ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,'.14+.12*'+seed),'Particles.Position':(POSITION,'lerp(User.PreviousPosition,User.CurrentPosition,'+seed+')'),
        'Particles.Velocity':(VEC3,'-User.FlightDirection*24+float3(0,0,-15)'),'Particles.SpriteSize':(VEC2,'float2(1.3,3.5)'),
        'Particles.Color':(COLOR,'float4(.25,.48,.6,.35)'),'Particles.SubImageIndex':(FLOAT,'0')})
    assignments(s,en,'ParticleUpdateScript',{'Particles.Position':(POSITION,'Particles.Position+Particles.Velocity*Engine.DeltaTime'),'Particles.Color':(COLOR,'float4(.25,.48,.6,.35*(1-Particles.NormalizedAge))'),
        'Particles.SpriteSize':(VEC2,'float2(1.3,3.5)*(1-.6*Particles.NormalizedAge)'),'Particles.SubImageIndex':(FLOAT,'0')})
    save(s)

def build():
    export=u.AssetExportTask();export.object=u.load_asset('/Game/NiagaraExamples/StaticMesh/SM_SimpleProjectile');export.filename=str(SRC/'SM_SimpleProjectile.fbx');export.automated=True;export.prompt=False;export.replace_identical=True
    u.Exporter.run_asset_export_task(export)
    tex=u.AssetImportTask();tex.filename=str(SRC/'ThirdParty/CrackedIceSelected/ci_cracks.png');tex.destination_path=DEST;tex.destination_name='T_IceCracks';tex.automated=True;tex.replace_existing=True;tex.save=True
    TOOLS.import_asset_tasks([tex]);texture=u.load_asset(DEST+'/T_IceCracks');texture.set_editor_property('srgb',False);texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS);save(texture)
    mat=ice();trail()
    mesh=u.AssetImportTask();mesh.filename=str(SRC/'SM_IceSpike.fbx');mesh.destination_path=DEST;mesh.destination_name='SM_IceSpike';mesh.automated=True;mesh.replace_existing=True;mesh.save=True
    options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.static_mesh_import_data.combine_meshes=True;options.static_mesh_import_data.auto_generate_collision=False;options.static_mesh_import_data.convert_scene_unit=True
    mesh.options=options;TOOLS.import_asset_tasks([mesh])
    imported=u.load_asset(DEST+'/SM_IceSpike');imported.set_material(0,mat);save(imported)
    for source,name in [('/Game/NiagaraExamples/StaticMesh/SM_GlassShard_01','SM_IceShard'),('/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Hit/P_Ice','P_IceSpikeImpact')]:
        path=DEST+'/'+name
        copy=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source,path)
        if isinstance(copy,u.StaticMesh):copy.set_material(0,mat)
        save(copy)
    bounds=imported.get_bounds()
    (SRC/'engine-authoring.json').write_text(json.dumps({'mesh':imported.get_path_name(),'extent_cm':str(bounds.box_extent),'origin_cm':str(bounds.origin),'material':mat.get_path_name(),'status':'imported and compiled; no game test or scene render'},indent=2),encoding='utf-8')
    task=u.AssetImportTask();task.filename=str(SRC/'ice_impact.wav');task.destination_path=DEST;task.destination_name='S_IceImpact';task.automated=True;task.replace_existing=True;task.save=True
    TOOLS.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('Ice impact audio import failed')
    # Retain editable mesh source for exact geometry inspection/adaptation.
    export=u.AssetExportTask();export.object=u.load_asset('/Game/NiagaraExamples/StaticMesh/SM_SimpleProjectile');export.filename=str(SRC/'SM_SimpleProjectile.fbx');export.automated=True;export.prompt=False;export.replace_identical=True
    u.Exporter.run_asset_export_task(export)
    u.log('ICE_SPIKE_ASSETS_AUTHORED')

if __name__=='__main__':build()
