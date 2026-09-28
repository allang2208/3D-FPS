"""Save continuous visual-only ocean shading using existing water textures."""
import json,hashlib,shutil
from datetime import datetime
from pathlib import Path
import unreal as u
ROOT=Path(__file__).parent;PROJECT=ROOT.parents[2]
DEST='/Game/Props/GodSpaceLayout20260927'
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
rebuild_clouds=globals().get('REBUILD_CLOUDS',True)
materials_only=globals().get('MATERIALS_ONLY',False)
if editor and editor.get_game_world() and not materials_only:raise RuntimeError('End PIE before importing ocean geometry')
paths=[DEST+'/Materials/'+n for n in ['M_GodSpaceDistantOcean','MI_GodSpaceDistantOcean','M_GodSpaceOceanFar','MI_GodSpaceOceanFar','M_GodSpaceCloudSea','MI_GodSpaceCloudSea']]+[DEST+'/Meshes/SM_GodSpaceDistantOcean']+[DEST+'/Textures/'+n for n in ['T_GodSpaceOceanSurface_N','T_GodSpaceOceanDetail_N']]
if not rebuild_clouds:paths=[p for p in paths if 'CloudSea' not in p]
if materials_only:paths=[p for p in paths if '/Materials/' in p]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths) and not globals().get('RESUME_OWNED_OCEAN',False):raise RuntimeError('Preserve unsaved ocean edits: '+str(dirty.intersection(paths)))
report={'saved':[],'backups':[],'runtime_tested':False,'coverage_target':.80,'coverage_measured':False}
backup=PROJECT/'trash/godspace-fountain-reuse-20260928'/datetime.now().strftime('%H%M%S-%f')
for path in paths:
    src=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    if src.exists():
        dst=backup/'Content'/src.relative_to(PROJECT/'Content')
        if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        report['backups'].append({'file':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})

def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing existing dependency '+path)
    return a

def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    report['saved'].append(a.get_path_name())
    (ROOT/'Receipts/ocean-import.json').write_text(json.dumps(report,indent=2),encoding='utf8')

def create(name,cls,factory):
    return u.load_asset(DEST+'/Materials/'+name) or TOOLS.create_asset(name,DEST+'/Materials',cls,factory)

textures=[]
for source,name in [('T_Water_Normal_Large','T_GodSpaceOceanSurface_N'),('T_Water_Normal_Subtle','T_GodSpaceOceanDetail_N')]:
    # Actual 2D tiling normals used by the library's ocean material. The former
    # 961x63 Ocean_Waves*_Normals assets are vertex-animation lookup data.
    tex=u.load_asset(DEST+'/Textures/'+name)
    if materials_only:
        textures.append(load(DEST+'/Textures/'+name))
        continue
    if not tex:tex=TOOLS.duplicate_asset(name,DEST+'/Textures',load('/Game/WaterMaterials/Textures/'+source))
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
    tex.set_editor_property('srgb',False);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
    tex.set_editor_property('max_texture_size',1024);tex.set_editor_property('never_stream',False)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP);tex.set_editor_property('address_y',u.TextureAddress.TA_WRAP)
    textures.append(tex);save(tex)

def node(cls):return L.create_material_expression(mat,cls)
def wire(a,b,pin,output=''):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Connection failed '+pin)
def prop(a,name,output=''):
    if not L.connect_material_property(a,output,getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Property failed '+name)
def scalar(name,value):
    n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def vector(name,value):
    n=node(u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def custom(code,inputs,width,label):
    n=node(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('description',label)
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for name in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins)
    for name,a in inputs.items():wire(a,n,name)
    return n

water=load('/Game/Props/RomanFountain20260917/Materials/MIC_FountainWaveWater')
noise_code=(ROOT/'OceanNoise.hlsl').read_text(encoding='utf8')

def ocean_material(near):
    global mat
    suffix='GodSpaceDistantOcean' if near else 'GodSpaceOceanFar'
    # Keep the previous four-band masters recoverable; the stable instances
    # referenced by the map now inherit the actual fountain-spectrum derivative.
    mat=create('M_'+suffix+'_FountainSpectrum',u.Material,u.MaterialFactoryNew())
    # UE 5.8 DeleteAllMaterialExpressions iterates the collection it removes from,
    # leaving old custom outputs behind. Snapshot it before deleting this owned graph.
    for old in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,old)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    # A SLW/DefaultLit boundary changes reflection/compositing even when the
    # albedo, normal and opacity match. This visual-only backdrop now uses the
    # same lit surface on both sides, without a separate water rendering pass.
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('two_sided',False);mat.set_editor_property('tangent_space_normal',False)
    pos=node(u.MaterialExpressionWorldPosition);pos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    clock=node(u.MaterialExpressionTime)
    variation=custom(noise_code+(ROOT/'OceanVariation.hlsl').read_text(encoding='utf8'),{'P':pos,'Clock':clock},2,'Smooth world-space wave groups, shared by near and far')
    radius=custom('return length(P.xy-float2(-2400,-1300));',{'P':pos},1,'Shared radial coverage centered beneath the hub')
    mix=custom('return smoothstep(180000,1080000,R*lerp(.90,1.10,V.x));',{'R':radius,'V':variation},1,'Broad irregular detail fade, fully matched by the 12 km section boundary')
    detail=custom('return 1-smoothstep(1200000,5000000,R);',{'R':radius},1,'Filter subpixel detail toward the horizon')
    base=custom('return normalize(P-float3(-2400,-1300,-636150000));',{'P':pos},3,'World-space spherical normal, independent of the mesh tangent fan')
    def normal_sample(texture,scale,velocity,rotation,offset,warp):
        cs,sn=rotation
        uvcode=f'float2 p=P.xy-float2(-2400,-1300); float2 q=float2(({cs})*p.x-({sn})*p.y,({sn})*p.x+({cs})*p.y); return q/float2({scale[0]},{scale[1]})+T*float2({velocity[0]},{velocity[1]})+float2({offset[0]},{offset[1]})+(V-.5)*{warp};'
        uv=custom(uvcode,{'P':pos,'T':clock,'V':variation},2,'Rotated, unequal-scale, smoothly warped water UVs')
        tex=node(u.MaterialExpressionTextureSample);tex.set_editor_property('texture',texture)
        tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL);wire(uv,tex,'UVs')
        return custom(f'return float3(({cs})*N.x+({sn})*N.y,-({sn})*N.x+({cs})*N.y,N.z);',{'N':tex},3,'Rotate decoded normal back into world axes')
    # Identical far shading on both sections: the section boundary has no UV,
    # colour, roughness or normal discontinuity. Far needs only this one sample.
    macro=normal_sample(textures[0],(77300.,102100.),(.0027,.0011),(.3907311,.9205049),(2.31,7.13),.73)
    far_normal=custom('return normalize(Base+float3(N.xy*.13*Detail,0));',{'Base':base,'N':macro,'Detail':detail},3,'Shared far normal including the same coordinate warp')
    color=vector('OceanColor',u.LinearColor(.009,.050,.075,1))
    far_color=custom('return Color.rgb*lerp(.96,1.04,V.y);',{'Color':color,'V':variation},3,'Continuous deep blue without wave-shaped albedo stripes')
    far_rough=custom('return lerp(.20,.32,1-Detail);',{'Detail':detail},1,'Distant highlight filtering')
    if near:
        geo_fade=custom('float2 p=(P.xy-float2(-2400,-1300))*.01; float r=length(p); float t=saturate((r-2200)/1600); float d=-6*t*(1-t)/1600; return float3(1-t*t*(3-2*t),d*p/max(r,1));',{'P':pos},3,'Height fade and gradient reach zero inside the regular 31.25 m grid')
        swell=custom((ROOT/'OceanSwell.hlsl').read_text(encoding='utf8'),{'P':pos,'Clock':clock},4,'Sixteen existing Clearwater fountain spectrum terms with analytic gradients')
        prop(custom('return float3(0,0,Wave.x*Fade.x);',{'Wave':swell,'Fade':geo_fade},3,'Bounded animated ocean displacement'),'WORLD_POSITION_OFFSET')
        a=normal_sample(textures[0],(21100.,15700.),(.013,.006),(.9205049,.3907311),(5.71,1.37),1.13)
        b=normal_sample(textures[1],(8100.,11300.),(-.017,.011),(.6560590,-.7547096),(2.93,8.17),.91)
        normal=custom('float2 slope=-(Wave.yz+Wave.x*.01*GeoFade.yz); slope+=A.xy*lerp(.10,.21,V.x)+B.xy*lerp(.13,.055,V.x); float3 close=normalize(Base+float3(slope,0)); return normalize(lerp(close,Far,Blend));',{'Base':base,'Wave':swell,'GeoFade':geo_fade,'A':a,'B':b,'Far':far_normal,'Blend':mix,'V':variation},3,'Reuse fountain analytic slopes after geometry fades; converge continuously to far water')
        uv=custom('float2 p=P.xy-float2(-2400,-1300); return float2(.819152*p.x-.573576*p.y,.573576*p.x+.819152*p.y)/float2(13700,19300)+T*float2(.0047,.0019)+(V-.5)*1.7;',{'P':pos,'T':clock,'V':variation},2,'Warped foam breakup independent of the ripple tiles')
        tex=node(u.MaterialExpressionTextureSample);noise_tex=load('/Game/WaterMaterials/Textures/T_Noises');tex.set_editor_property('texture',noise_tex)
        tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if noise_tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(uv,tex,'UVs')
        foam=custom('return smoothstep(.48,.82,F.r)*smoothstep(.18,.44,Wave.w)*lerp(.035,.11,V.y)*GeoFade.x*(1-Blend);',{'F':tex,'Wave':swell,'GeoFade':geo_fade,'Blend':mix,'V':variation},1,'Reuse fountain noise texture for sparse crest breakup')
        prop(normal,'NORMAL')
        prop(custom('return lerp(Far*float3(.94,1.10,1.08),Far,Blend)+float3(.48,.55,.57)*Foam;',{'Foam':foam,'Far':far_color,'Blend':mix},3,'Mild near tint converges to the exact same far color'),'BASE_COLOR')
        prop(custom('return lerp(lerp(.09,.13,V.y)+Foam*.20,Far,Blend);',{'Foam':foam,'Far':far_rough,'Blend':mix,'V':variation},1,'Fountain-like glossy highlights, progressively filtered toward the horizon'),'ROUGHNESS')
    else:
        prop(far_normal,'NORMAL');prop(far_color,'BASE_COLOR');prop(far_rough,'ROUGHNESS')
    prop(scalar('WaterSpecular',.255),'SPECULAR')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Ocean material compilation failed: '+str(errors))
    save(mat)
    inst=create('MI_'+suffix,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(inst,mat);L.update_material_instance(inst);save(inst)
    return inst

mi=ocean_material(True);far_mi=ocean_material(False)

# Use the cloud-sea authoring entry so a later full layout rebuild retains its
# percentile footprint, variable tops, weather contracts and distance budgets.
if rebuild_clouds:
    cloud_file=ROOT/'build_cloud_sea.py'
    cloud_scope={'__file__':str(cloud_file),'__name__':'godspace_cloud_builder'}
    exec(compile(cloud_file.read_text(encoding='utf8'),str(cloud_file),'exec'),cloud_scope)
    cloudmi=cloud_scope['build']()
    report['saved'].extend([DEST+'/Materials/M_GodSpaceCloudSea',cloudmi.get_path_name()])

if not materials_only:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.import_uniform_scale=1
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.reorder_material_to_fbx_order=True
    d.set_editor_property('distance_field_resolution_scale',0.);d.set_editor_property('generate_lightmap_u_vs',False)
    t=u.AssetImportTask();t.filename=str(ROOT/'Exported/SM_GodSpaceDistantOcean.fbx');t.destination_path=DEST+'/Meshes';t.destination_name='SM_GodSpaceDistantOcean'
    t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.options=opt;TOOLS.import_asset_tasks([t])
    mesh=load(DEST+'/Meshes/SM_GodSpaceDistantOcean')
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        slotname=str(slot.get_editor_property('imported_material_slot_name')).lower()
        mesh.set_material(index,far_mi if 'far' in slotname else mi)
    budget_file=ROOT/'ocean_mesh_budget.py';budget_namespace={'__file__':str(budget_file),'__name__':'ocean_mesh_budget'}
    exec(compile(budget_file.read_text(encoding='utf8'),str(budget_file),'exec'),budget_namespace)
    budget_namespace['apply'](mesh)
    save(mesh)
report.update(complete=True,texture_samples_near=4,texture_samples_far=1,spectrum_terms=16,normal_texture_max_size=1024,normal_texture_compression='BC5',water_source=water.get_path_name(),wave_reuse=json.loads((ROOT/'Receipts/ocean-reused-spectrum.json').read_text()),cloud_assets_changed=rebuild_clouds,mesh_changed=not materials_only,shading_model_near_and_far='DefaultLit',single_layer_water_pass=False,displacement_fade_m=[2200,3800],detail_transition_m=[1800,12000],authored=json.loads((ROOT/'Receipts/ocean-authored.json').read_text()),interactions=False,simulation=False,water_actor_tick=False,additional_cloud_layers=0)
(ROOT/'Receipts/ocean-import.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GODSPACE_OCEAN_ASSETS_SAVED '+json.dumps({'saved':report['saved'],'triangles':report['authored']['triangles'],'runtime_tested':False}))
