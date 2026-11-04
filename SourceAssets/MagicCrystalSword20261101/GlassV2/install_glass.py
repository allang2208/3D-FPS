"""Author mode 9 glass from the current crystal parent; never change other finishes."""
from pathlib import Path
import json, runpy
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary
SOURCE='/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915/M_FrostCrystalSword_SeamlessBronze'
DEST='/Game/Weapons/FrostCrystalSword20260915/HighEnergyGlass20261102'
WORLD=DEST+'/M_FrostCrystalSword_HighEnergyGlass'
PREVIEW=DEST+'/M_FrostCrystalSword_HighEnergyGlass_Preview'
REV='HighEnergyGlassV2'
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE active: preserve materials')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name() in (SOURCE,WORLD,PREVIEW):
        raise RuntimeError('Preserve unsaved material '+package.get_path_name())

def build(path,preview):
    if E.does_asset_exist(path):
        mat=E.load_asset(path)
        if E.get_metadata_tag(mat,'HighEnergyGlassRevision') in (REV,'HighEnergyGlassV3Dense20261103','HighEnergyDenseCrystalV4_20261103'):
            return mat
        raise RuntimeError('Preserve existing different material '+path)
    mat=E.duplicate_asset(SOURCE,path)
    if not mat: raise RuntimeError('Cannot duplicate '+SOURCE)
    def node(cls,**props):
        n=L.create_material_expression(mat,cls)
        for k,v in props.items(): n.set_editor_property(k,v)
        return n
    def wire(src,dst,pin,out=''):
        names=[str(x) for x in L.get_material_expression_input_names(dst)]
        norm=lambda x:x.replace(' ','').replace('_','').lower()
        actual=next((x for x in names if norm(x)==norm(pin)),None)
        if actual is None and pin=='Input' and len(names)==1: actual=names[0]
        if actual is None or not L.connect_material_expressions(src,out,dst,actual):
            raise RuntimeError('Cannot connect '+pin+' '+str(names))
    def output(src,field,out=''):
        if not L.connect_material_property(src,out,getattr(u.MaterialProperty,'MP_'+field)):
            raise RuntimeError('Cannot connect '+field)
    def root(field):
        prop=getattr(u.MaterialProperty,'MP_'+field)
        n=L.get_material_property_input_node(mat,prop)
        return n,str(L.get_material_property_input_node_output_name(mat,prop)) if n else ''
    def scalar(v): return node(u.MaterialExpressionConstant,r=float(v))
    def parameter(name,v): return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=float(v))
    def color(v): return node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
    def custom(label,code,width,**inputs):
        n=node(u.MaterialExpressionCustom,desc=REV+' '+label,code=code,
               output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
        pins=[]
        for key in inputs:
            p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        n.set_editor_property('inputs',pins)
        for key,value in inputs.items():
            src,out=value if isinstance(value,tuple) else (value,'')
            wire(src,n,key,out)
        return n

    old={f:root(f) for f in ('BASE_COLOR','METALLIC','SPECULAR','NORMAL','ROUGHNESS','EMISSIVE_COLOR','FRONT_MATERIAL')}
    if not old['FRONT_MATERIAL'][0] or not old['BASE_COLOR'][0]:
        raise RuntimeError('Missing current crystal PBR graph')
    for n in L.get_material_expressions(mat):
        if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='BladeFinishMode':
            n.set_editor_property('default_value',9.)

    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT if preview else u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE)
    mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    mat.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    mat.set_editor_property('two_sided',False)
    mat.set_editor_property('is_thin_surface',False)
    mat.set_editor_property('screen_space_reflections',not preview)
    mat.set_editor_property('forward_blends_sky_light_cubemaps',True)
    mat.set_editor_property('allow_front_layer_translucency',True)
    mat.set_editor_property('refraction_method',u.RefractionMode.RM_NONE if preview else u.RefractionMode.RM_INDEX_OF_REFRACTION)
    # The surface mask uses the original UV/color contract, not hue after wetness.
    raw=node(u.MaterialExpressionTextureSample,texture=E.load_asset('/Game/Weapons/FrostCrystalSword20260915/T_FrostCrystalSword_BaseColor'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    vertex=node(u.MaterialExpressionVertexColor)
    mask=custom('original crystal versus opaque bronze seat',
        'float peak=max(Base.g,Base.b);return smoothstep(.035,.18,(peak-Base.r)/max(peak,.001))*(1-Guard);',
        1,Base=(raw,'RGB'),Guard=(vertex,'R'))
    world=node(u.MaterialExpressionWorldPosition)
    local=node(u.MaterialExpressionTransformPosition,
        transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
        transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    wire(world,local,'Input')
    # Blade width is X; Y is its thickness. Bounded optical depth follows the
    # central ridge and native texture, without inventing bright painted lines.
    thickness=custom('bounded ridge optical thickness cm',
        'float ridge=saturate(1-abs(P.x)/5.2);float detail=dot(Base,float3(.2126,.7152,.0722));'
        'return (.65+1.65*ridge)*lerp(.9,1.1,saturate(detail));',1,P=local,Base=(raw,'RGB'))
    transmission=custom('clear cyan volume absorption',
        'return .55*exp(-float3(.23,.07,.035)*Thickness*Density);',3,
        Thickness=thickness,Density=parameter('CrystalDensity',1.))
    normal=custom('polished large facets',
        'return normalize(float3(N.xy*Strength,lerp(1.0,N.z,Strength)));',3,
        N=old['NORMAL'] if old['NORMAL'][0] else color((0,0,1)),Strength=parameter('CrystalNormalStrength',.18))
    rough=custom('clean glass roughness',
        'return clamp(Polish+R*.035,.045,.11);',1,
        R=old['ROUGHNESS'] if old['ROUGHNESS'][0] else scalar(.5),Polish=parameter('CrystalPolish',.055))
    f0=custom('dielectric reflectance', 'float f=(IOR-1)/(IOR+1);return f*f;',1,IOR=parameter('CrystalIOR',1.52))
    emission=old['EMISSIVE_COLOR'] if old['EMISSIVE_COLOR'][0] else (color((0,0,0)),'')
    if not preview:
        slab=node(u.MaterialExpressionSubstrateSlabBSDF)
        simple=next(getattr(u.MaterialSubSurfaceType,n) for n in dir(u.MaterialSubSurfaceType) if 'SIMPLE' in n and 'VOLUME' in n)
        slab.set_editor_property('sub_surface_type',simple)
        mfp=node(u.MaterialExpressionSubstrateTransmittanceToMFP)
        wire(transmission,mfp,'TransmittanceColor');wire(scalar(.01),mfp,'Thickness')
        wire(mfp,slab,'SSS MFP','MFP')
        wire(color((.008,.019,.024)),slab,'Diffuse Albedo')
        wire(f0,slab,'F0');wire(scalar(1),slab,'F90')
        wire(rough,slab,'Roughness');wire(normal,slab,'Normal')
        wire(emission[0],slab,'Emissive Color',emission[1])
        mix=node(u.MaterialExpressionSubstrateHorizontalMixing,use_parameter_blending=True)
        wire(old['FRONT_MATERIAL'][0],mix,'Background',old['FRONT_MATERIAL'][1])
        wire(slab,mix,'Foreground');wire(mask,mix,'Mix');output(mix,'FRONT_MATERIAL')
        output(scalar(1),'OPACITY')
        # Screen refraction is restrained for a thin handheld blade. Optical
        # reflectance still uses IOR 1.52 above, independently of screen offset.
        refraction=custom('subtle crystal refraction','return lerp(1.0,IOR,Mask);',1,IOR=parameter('CrystalScreenIOR',1.025),Mask=mask)
        output(refraction,'REFRACTION')
    else:
        # UI captures require ordinary inverse-coverage alpha. Share the same
        # absorption and polished normals, preserving the original metal seat.
        facing=node(u.MaterialExpressionFresnel,exponent=5.,base_reflect_fraction=0.)
        alpha=custom('capture coverage',
            'float F=lerp(F0,1,Facing);float A=1-dot(T,float3(.2126,.7152,.0722))*(1-F);return lerp(1,clamp(A,.2,.94),Mask);',
            1,F0=f0,Facing=facing,T=transmission,Mask=mask)
        fields={
            'BASE_COLOR':custom('preview crystal tint','return lerp(Base,float3(.075,.24,.31),Mask);',3,Base=old['BASE_COLOR'],Mask=mask),
            'METALLIC':custom('dielectric crystal','return lerp(Base,0,Mask);',1,Base=old['METALLIC'] if old['METALLIC'][0] else scalar(0),Mask=mask),
            'SPECULAR':custom('preview specular','return lerp(.5,F0/.08,Mask);',1,F0=f0,Mask=mask),
            'ROUGHNESS':custom('preserve seat roughness','return lerp(Base,Glass,Mask);',1,Base=old['ROUGHNESS'],Glass=rough,Mask=mask),
            'NORMAL':custom('preserve seat normal','return normalize(lerp(Base,Glass,Mask));',3,Base=old['NORMAL'],Glass=normal,Mask=mask),
            'OPACITY':alpha,
        }
        front=node(u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for field,pin in [('BASE_COLOR','BaseColor'),('METALLIC','Metallic'),('SPECULAR','Specular'),('ROUGHNESS','Roughness'),('NORMAL','Normal'),('OPACITY','Opacity')]:
            output(fields[field],field);wire(fields[field],front,pin)
        wire(emission[0],front,'EmissiveColor',emission[1]);output(front,'FRONT_MATERIAL')
    if not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in L.get_material_expressions(mat)):
        temporal=node(u.MaterialExpressionTemporalResponsivenessOutput)
        if not L.connect_material_expressions(scalar(1),'',temporal,''):
            raise RuntimeError('Temporal response connection failed')
    errors=L.recompile_material(mat)
    if errors: raise RuntimeError('Glass compile errors '+str(errors))
    L.get_statistics(mat)
    E.set_metadata_tag(mat,'HighEnergyGlassRevision',REV)
    if not E.save_loaded_asset(mat,False): raise RuntimeError('Cannot save '+path)
    return mat

saved=[build(WORLD,False).get_path_name(),build(PREVIEW,True).get_path_name()]
runpy.run_path(str(P.parent/'DenseCrystalV4/install_materials.py'))
(P/'material-receipt.json').write_text(json.dumps(dict(revision='HighEnergyDenseCrystalV4_20261103',assets_saved=saved,
    source_preserved=SOURCE,world_transmittance='dense explicit coverage',preview_transmittance='dense explicit coverage',
    gameplay_tested=False,visual_tested=False),indent=2)+'\n',encoding='utf8')
u.log('HIGH_ENERGY_GLASS_ASSETS_SAVED '+str(len(saved)))
