"""Build the owned cloud-sea material using existing weather/noise textures."""
import hashlib
import json
import runpy
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).parent
PROJECT=ROOT.parents[2]
DEST='/Game/Props/GodSpaceLayout20260927/Materials'
L=u.MaterialEditingLibrary
E=u.EditorAssetLibrary

def build():
    paths=[DEST+'/M_GodSpaceCloudSea_Cumulus',DEST+'/MI_GodSpaceCloudSea',DEST+'/VT_GodSpaceCloudNoise_LinearMips']
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(paths):raise RuntimeError('Preserve unsaved cloud assets: '+str(dirty.intersection(paths)))
    settings=json.loads((ROOT/'CloudSeaSources/distribution.json').read_text(encoding='utf8'))
    sources=json.loads((ROOT/'CloudSeaSources/sources.json').read_text(encoding='utf8'))
    report={'saved':[],'backups':[],'distribution':settings,'runtime_tested':False}
    backup=PROJECT/'trash/godspace-cumulus-20260928'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    for path in paths:
        src=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        if not src.exists():continue
        dst=backup/'Content'/src.relative_to(PROJECT/'Content')
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        report['backups'].append({'file':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
    mat=u.load_asset(paths[0]);mi=u.load_asset(paths[1])
    if not mi:raise RuntimeError('Existing cloud-sea material instance is required')
    if not mat:mat=u.AssetToolsHelpers.get_asset_tools().create_asset('M_GodSpaceCloudSea_Cumulus',DEST,u.Material,u.MaterialFactoryNew())
    noise=u.load_asset(paths[2]) or E.duplicate_asset(sources['Noise_Texture3D']['path'],paths[2])
    if not mat or not noise:raise RuntimeError('Cannot create the owned cumulus assets')
    # Keep the engine/shared texture untouched. Density data must not undergo a
    # color-space transform, and distance LOD needs actual volume mip levels.
    noise.set_editor_property('srgb',False)
    noise.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
    noise.set_editor_property('filter',u.TextureFilter.TF_TRILINEAR)
    noise.set_editor_property('address_mode',u.TextureAddress.TA_WRAP)
    for old in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,old)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_VOLUME)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    # Volume domain alone does not compile the VolumetricCloud renderer's
    # permutations. Commandlet authoring must explicitly persist this usage.
    mat.set_editor_property('used_with_volumetric_cloud',True)

    def node(cls):return L.create_material_expression(mat,cls)
    def wire(a,b,pin,output=''):
        if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect '+pin)
    def scalar(name,value):
        n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
    def vector(name,value):
        n=node(u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*value));return n
    def prop(n,p):
        if not L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+p)):raise RuntimeError('Cannot connect volume '+p)
    def custom(code,inputs,width,description):
        n=node(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('desc',description)
        n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
        pins=[]
        for name in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        n.set_editor_property('inputs',pins)
        for name,value in inputs.items():
            if isinstance(value,tuple):wire(value[0],n,name,value[1])
            else:wire(value,n,name)
        return n
    def texture(name):
        tex=noise if name=='Noise_Texture3D' else u.load_asset(sources[name]['path'])
        if not tex:raise RuntimeError('Missing existing cloud source: '+name)
        n=node(u.MaterialExpressionTextureObjectParameter)
        n.set_editor_property('parameter_name',name);n.set_editor_property('texture',tex)
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        return n

    pos=node(u.MaterialExpressionWorldPosition)
    # VolumetricCloudMaterialPixelCommon.ush updates AbsoluteWorldPosition for
    # each ray sample. Its WorldPosition_NoOffsets fields are explicitly TODO
    # and remain uninitialized for this path; using them flattens the cloud map.
    pos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_DEFAULT)
    camera=node(u.MaterialExpressionCameraPositionWS)
    attribute=node(u.MaterialExpressionCloudSampleAttribute)
    clock=custom('return lerp(EditorClock,WeatherClock,saturate(Driven));',{
        'EditorClock':node(u.MaterialExpressionTime),'WeatherClock':scalar('FPS_CloudMotionTime',0),
        'Driven':scalar('FPS_CloudMotionDriven',0)},1,'Reuse the weather system integrated cloud clock')
    placement=vector('Layout_GlobalTexturePlacement',(0,0,0,0))
    scale=scalar('Layout_CloudGlobalScale',settings['layout_period_km'])
    density=scalar('Cloud_GlobalDensity',settings['base_density_per_m'])
    weather=scalar('FPS_WeatherBlend',0)
    support=custom((ROOT/'CloudSeaCumulusCoverage.hlsl').read_text(encoding='utf8'),{
        'P':pos,'Camera':camera,'H':(attribute,'NormAltitudeInLayer'),
        'Pattern':texture('Layout_CloudGlobalPattern'),'Placement':placement,'LayoutScale':scale,
        'Threshold':scalar('GodSpace_CoverageThreshold',settings['threshold']),
        'Feather':scalar('GodSpace_CoverageFeather',settings['feather'])},3,'Weather footprint, rounded height profile and conservative empty-space skip')
    advanced=node(u.MaterialExpressionVolumetricAdvancedMaterialOutput)
    advanced.set_editor_property('multi_scattering_approximation_octave_count',1)
    advanced.set_editor_property('const_multi_scattering_contribution',.65)
    advanced.set_editor_property('const_multi_scattering_occlusion',.40)
    advanced.set_editor_property('const_multi_scattering_eccentricity',.30)
    advanced.set_editor_property('const_phase_g',.50)
    advanced.set_editor_property('const_phase_g2',-.16)
    advanced.set_editor_property('const_phase_blend',.26)
    advanced.set_editor_property('per_sample_phase_evaluation',False)
    advanced.set_editor_property('ground_contribution',False)
    advanced.set_editor_property('ray_march_volume_shadow',True)
    wire(support,advanced,'ConservativeDensity')
    cached=node(u.MaterialExpressionVolumetricAdvancedMaterialInput)
    field=custom((ROOT/'CloudSeaCumulusDensity.hlsl').read_text(encoding='utf8'),{
        'P':pos,'Camera':camera,'H':(attribute,'NormAltitudeInLayer'),
        'ShadowDistance':(attribute,'ShadowSampleDistance'),
        'Support':(cached,'ConservativeDensity as Float3'),
        'Noise':texture('Noise_Texture3D'),'Placement':placement,'LayoutScale':scale,
        'Clock':clock,'Density':density,'Weather':weather},1,'Cloud lobes and bounded edge erosion with distance-conditional sampling')
    extinction=custom('return D.xxx;',{'D':field},3,'Neutral extinction retains lighting colors')
    prop(extinction,'SUBSURFACE_COLOR')
    albedo=vector('Cloud_AlbedoColor',(.98,.985,.99,1))
    prop(custom('return clamp(C.rgb,float3(.94,.95,.96),float3(.99,.995,1));',{'C':albedo},3,'White cloud droplets with subtle cool tint'),'BASE_COLOR')
    # Connect the same MPC lightning envelope and weather-driven energy as the
    # shared cloud system, without introducing another storm timer or sky layer.
    lightning=runpy.run_path(str(PROJECT/'Tools/Weather/build_storm_lightning_materials.py'))
    lightning['connect_cloud_lightning'](mat,extinction,density)
    # No ambient-fill emission or compensating albedo: native cloud scattering
    # owns daylight/night color. Only the existing lightning MPC emits light.
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Cloud-sea material compilation failed: '+str(errors))
    report['final_shader_compile_errors']=list(errors)
    L.set_material_instance_parent(mi,mat)
    for name,value in {
        'GodSpace_CoverageThreshold':settings['threshold'],'GodSpace_CoverageFeather':settings['feather'],
        'Cloud_GlobalDensity':settings['base_density_per_m'],'Layout_CloudGlobalScale':settings['layout_period_km'],
        'FPS_WeatherBlend':0.,'FPS_CloudMotionDriven':0.,'FPS_CloudMotionTime':0.,
    }.items():L.set_material_instance_scalar_parameter_value(mi,name,value)
    L.set_material_instance_vector_parameter_value(mi,'Cloud_AlbedoColor',u.LinearColor(.98,.985,.99,1))
    L.set_material_instance_vector_parameter_value(mi,'Layout_GlobalTexturePlacement',u.LinearColor(0,0,0,0))
    L.set_material_instance_texture_parameter_value(mi,'Noise_Texture3D',noise)
    L.update_material_instance(mi)
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
    for asset in [noise,mat,mi]:
        if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save cloud-sea asset '+asset.get_path_name())
        report['saved'].append(asset.get_path_name())
    report.update(complete=True,texture_samples_primary_near=3,texture_samples_primary_medium=2,
        texture_samples_primary_far=2,cloud_layers=1,detail_fade_m=[2500,6500],
        body_noise_fade_m=None,horizon_fade_km=[100,150],
        weather_driven=True,cloud_assets_only=True,coverage_measured_in_game=False,
        lighting='native scattering; lightning emission only',noise_linear_mips=True,
        used_with_volumetric_cloud=True,
        density_reference='Takram three-geospatial ce69b0997845b125f3b0b59134b493d9813ae4a6')
    (ROOT/'Receipts/cloud-sea-authored.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('GODSPACE_CLOUD_SEA_MATERIAL_SAVED '+json.dumps(report))
    return mi

if __name__=='__main__':build()
