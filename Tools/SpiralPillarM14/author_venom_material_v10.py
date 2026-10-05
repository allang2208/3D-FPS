"""Refine the three owned M14 materials in place; compile and save, no game/test."""
from pathlib import Path
import json, shutil, sys, traceback
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
OUT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV10'
DEST='/Game/Monsters/SpiralPillarM14/VenomV09'
TAG='M14V10 '
L=u.MaterialEditingLibrary
E=u.EditorAssetLibrary
sys.path.insert(0,str(PROJECT/'Tools/Fluids'))
from author_river_pilot import node, wire, prop

report={'complete':False,'saved':[],'tested':False,'rendered':False,
        'native_code_changed':False,'shared_materials_modified':False}
(OUT/'Records').mkdir(parents=True,exist_ok=True)

def record():
    (OUT/'Records/assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def code(name):
    return (OUT/'Shaders'/(name+'.hlsl')).read_text(encoding='utf8')

def owned(m,cls,label):
    desc=TAG+label
    found=next((n for n in L.get_material_expressions(m)
                if isinstance(n,cls) and n.get_editor_property('desc')==desc),None)
    if found:return found
    result=node(m,cls)
    result.set_editor_property('desc',desc)
    return result

def custom(m,label,source,inputs,width=1):
    result=owned(m,u.MaterialExpressionCustom,label)
    result.set_editor_property('description',TAG+label)
    result.set_editor_property('code',source)
    result.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    current=[str(pin.get_editor_property('input_name')) for pin in result.get_editor_property('inputs')]
    if current!=list(inputs):result.set_editor_property('inputs',pins)
    for name,value in inputs.items():wire(value,result,name)
    return result

def parameter(m,label,value):
    result=owned(m,u.MaterialExpressionScalarParameter,label)
    result.set_editor_property('parameter_name',label)
    result.set_editor_property('default_value',value)
    return result

def configure(m,thin=False,film=False):
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE if thin else u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_THIN_TRANSLUCENT if thin else u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided',film)
    m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    m.set_editor_property('disable_depth_test',False)
    m.set_editor_property('allow_front_layer_translucency',False)
    m.set_editor_property('output_translucent_velocity',False)
    m.set_editor_property('refraction_method',u.RefractionMode.RM_PIXEL_NORMAL_OFFSET if thin else u.RefractionMode.RM_NONE)

def surface(m,inputs,thin=False,transmittance=None,coverage=None):
    result=owned(m,u.MaterialExpressionSubstrateShadingModels,'Surface')
    result.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_THIN_TRANSLUCENT if thin else u.MaterialShadingModel.MSM_DEFAULT_LIT)
    names={'BASE_COLOR':'BaseColor','ROUGHNESS':'Roughness','SPECULAR':'Specular','OPACITY':'Opacity','NORMAL':'Normal'}
    for name,value in inputs.items():
        prop(m,value,name);wire(value,result,names[name])
    if thin:
        wire(transmittance,result,'Thin Translucent Transmittance Color')
        wire(coverage,result,'Thin Translucent Surface Coverage')
        # UE 5.8 validates this output even with an explicit Substrate front surface.
        legacy=owned(m,u.MaterialExpressionThinTranslucentMaterialOutput,'TransmissionOutput')
        pins=L.get_material_expression_input_names(legacy)
        wire(transmittance,legacy,str(pins[0]))
        wire(coverage,legacy,str(pins[1]))
    prop(m,result,'FRONT_MATERIAL')

def liquid(m,core=False):
    configure(m,thin=not core)
    expressions=L.get_material_expressions(m)
    flow=next(n for n in expressions if isinstance(n,u.MaterialExpressionCustom)
              and n.get_editor_property('description').endswith('LiquidFlow'))
    flow.set_editor_property('code',code('M14LiquidFlow'))
    position=next(n for n in expressions if isinstance(n,u.MaterialExpressionLocalPosition))
    facing=owned(m,u.MaterialExpressionFresnel,'ChordFacing')
    facing.set_editor_property('exponent',1.)
    facing.set_editor_property('base_reflect_fraction',0.)
    vertex_normal=owned(m,u.MaterialExpressionVertexNormalWS,'GeometricNormal')
    wire(vertex_normal,facing,'Normal')
    thickness=custom(m,'OpticalThickness',code('M14OpticalThickness'),{'P':position,'Facing':facing,'Flow':flow})
    normal=custom(m,'WetNormal','return normalize(float3(F.xy*(1-.45*F.w),1));',{'F':flow},3)
    if core:
        # Low-coverage suspended tissue; no opaque sphere and no refractive inner interface.
        alpha=custom(m,'CloudCoverage',
            'float patches=smoothstep(.31,.73,F.z);float edge=pow(saturate(1-V),1.5);'
            'return (.025+.29*patches)*edge*(1-.35*F.w)*saturate(T*.16);',
            {'F':flow,'V':facing,'T':thickness})
        tint=custom(m,'CloudTint','return lerp(float3(.043,.054,.014),float3(.15,.16,.061),F.z);',{'F':flow},3)
        rough=custom(m,'CloudRoughness','return .23+.10*F.z;',{'F':flow})
        surface(m,{'BASE_COLOR':tint,'OPACITY':alpha,'NORMAL':normal,'ROUGHNESS':rough,'SPECULAR':parameter(m,'CloudSpecular',.12)})
    else:
        # Beer-Lambert transmission: cm-scaled chord, stronger blue absorption.
        trans=custom(m,'Transmission',
            'float3 sigma=float3(.073,.057,.157)*Strength;'
            'return exp(-sigma*T*(1-.22*F.w));',
            {'T':thickness,'F':flow,'Strength':parameter(m,'AbsorptionStrength',1.)},3)
        rough=custom(m,'WetRoughness','return clamp(.064+.046*F.z+.025*F.w,.06,.14);',{'F':flow})
        coverage=parameter(m,'LiquidSurfaceCoverage',1.)
        surface(m,{'ROUGHNESS':rough,'SPECULAR':parameter(m,'WetSpecular',.26),'NORMAL':normal},
                thin=True,transmittance=trans,coverage=coverage)
        refract=custom(m,'SubtleRefraction',
            'return 1+Amount*smoothstep(.05,3,T)*(1-.4*F.w);',
            {'T':thickness,'F':flow,'Amount':parameter(m,'RefractionOffset',.08)})
        prop(m,refract,'REFRACTION')

def film(m):
    configure(m,thin=True,film=True)
    field=next(n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
               and n.get_editor_property('description')=='M14V09 ContactFilm')
    field.set_editor_property('code',code('M14ContactFilm'))
    uv=next(n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureCoordinate))
    coverage=custom(m,'FilmCoverage','return F.x;',{'F':field})
    trans=custom(m,'FilmTransmission','return exp(-float3(2.6,2.0,5.6)*F.y);',{'F':field},3)
    rough=custom(m,'FilmRoughness','return .075+.038*F.z;',{'F':field})
    normal=custom(m,'FilmNormal','float2 p=(UV-.5)*2;return normalize(float3(p*F.w*.044*F.x,1));',{'UV':uv,'F':field},3)
    spec=custom(m,'FilmSpecular','return .26*F.x;',{'F':field})
    surface(m,{'ROUGHNESS':rough,'NORMAL':normal,'SPECULAR':spec},thin=True,transmittance=trans,coverage=coverage)
    refract=custom(m,'FilmRefraction','return 1+.025*F.x*saturate(F.y*12);',{'F':field})
    prop(m,refract,'REFRACTION')

def main(resume_own_edits=False):
    paths=[DEST+'/M_M14_Venom'+role for role in ('Body','Core','Film')]
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(paths) and not resume_own_edits:
        raise RuntimeError('Preserve unsaved target material edits: '+str(dirty.intersection(paths)))
    # Backup only these three owned assets once, before any graph changes.
    backup=OUT/'BackupV09';backup.mkdir(parents=True,exist_ok=True)
    for path in paths:
        src=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        dst=backup/src.name
        if not dst.exists():shutil.copy2(src,dst)
    materials=[u.load_asset(path) for path in paths]
    liquid(materials[0]);liquid(materials[1],core=True);film(materials[2])
    for mat in materials:
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError(str(errors))
    u.PoisonMaggotMonster.compile_material_assets(materials)
    for mat in materials:
        if not E.save_loaded_asset(mat,False):raise RuntimeError('Could not save '+mat.get_path_name())
        report['saved'].append(mat.get_path_name());record()
    report.update(complete=True,materials=report['saved'],user_testing_pending=True,
                  new_textures=0,new_particles=0,refraction='pixel_normal_offset',
                  absorption='approximate chord in cm, colored Beer-Lambert transmission',
                  source_revision='ProductionV10',runtime_asset_directory='VenomV09')
    record();print('M14_V10_LIQUID_MATERIALS_SAVED')

if __name__=='__main__':
    try:main(globals().get('M14_RESUME_OWN_EDITS',False))
    except Exception:
        report['error']=traceback.format_exc();record();raise
