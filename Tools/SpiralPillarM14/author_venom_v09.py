"""Author M14-specific viscous liquid variants and a pooled contact film."""
from pathlib import Path
import json,sys,traceback
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
OUT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV09'
(OUT/'Records').mkdir(parents=True,exist_ok=True)
DEST='/Game/Monsters/SpiralPillarM14/VenomV09'
sys.path.insert(0,str(PROJECT/'Tools/Fluids'))
from author_river_pilot import node,wire,prop,scalar,custom
from author_impact_smoke_corrosion import surface,constant
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
report={'complete':False,'saved':[],'tested':False,'rendered':False}

def record():(OUT/'Records/assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
    report['saved'].append(obj.get_path_name());record()
def code(name):return (OUT/'Shaders'/(name+'.hlsl')).read_text(encoding='utf8')

def liquid(role):
    path=DEST+'/M_M14_Venom'+role
    mat=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Fluids/VenomProjectiles20260924/M_Venom'+role,path)
    shapes=[]
    for expr in L.get_material_expressions(mat):
        if not isinstance(expr,u.MaterialExpressionCustom):continue
        label=expr.get_editor_property('description')
        if label.endswith('LiquidShape'):expr.set_editor_property('code',code('M14LiquidShape'));shapes.append(expr)
        elif label.endswith('LiquidFlow'):expr.set_editor_property('code',code('M14LiquidFlow'))
    for shape in shapes:
        pins=list(shape.get_editor_property('inputs'))
        if not any(str(pin.get_editor_property('input_name'))=='Age' for pin in pins):
            pin=u.CustomInput();pin.set_editor_property('input_name','Age');pins.append(pin)
            shape.set_editor_property('inputs',pins)
        age=next((n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionScalarParameter)
            and str(n.get_editor_property('parameter_name'))=='M14FlightAge'),None)
        if age is None:age=scalar(mat,'M14FlightAge',0.)
        age.set_editor_property('use_custom_primitive_data',True);age.set_editor_property('primitive_data_index',1)
        wire(age,shape,'Age')
    if not shapes:raise RuntimeError('Dedicated liquid has no source deformation node')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat);return mat

def film():
    path=DEST+'/M_M14_VenomFilm'
    mat=u.load_asset(path) if E.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset('M_M14_VenomFilm',DEST,u.Material,u.MaterialFactoryNew())
    marker='M14V09 ContactFilm'
    existing=next((n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')==marker),None)
    if existing:existing.set_editor_property('code',code('M14ContactFilm'))
    else:
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        mat.set_editor_property('two_sided',True)
        mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        mat.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        mat.set_editor_property('disable_depth_test',False)
        mat.set_editor_property('refraction_method',u.RefractionMode.RM_NONE)
        L.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
        uv=node(mat,u.MaterialExpressionTextureCoordinate)
        inputs={'UV':uv}
        for index,name in enumerate(('Opacity','Seed','Age')):
            data=node(mat,u.MaterialExpressionPerInstanceCustomData)
            data.set_editor_property('data_index',index)
            interp=node(mat,u.MaterialExpressionVertexInterpolator);wire(data,interp,str(L.get_material_expression_input_names(interp)[0]))
            inputs[name]=interp
        field=custom(mat,code('M14ContactFilm'),inputs,4,marker)
        tint=custom(mat,'return lerp(float3(.025,.065,.006),float3(.13,.24,.025),F.y)+F.z*float3(.045,.055,.012);',{'F':field},3)
        opacity=custom(mat,'return F.x;',{'F':field})
        rough=custom(mat,'return .10+.10*F.z;',{'F':field})
        normal=custom(mat,'float2 p=(UV-.5)*2;return normalize(float3(p*F.w*.13,1));',{'UV':uv,'F':field},3)
        surface(mat,{'BASE_COLOR':tint,'OPACITY':opacity,'ROUGHNESS':rough,'NORMAL':normal,'SPECULAR':constant(mat,.62)})
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    save(mat);return mat

def main():
    E.make_directory(DEST)
    materials=[liquid('Body'),liquid('Core'),film()]
    u.PoisonMaggotMonster.compile_material_assets(materials)
    for material in materials:save(material)
    bp=u.load_asset('/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14')
    cdo=u.get_default_object(bp.generated_class())
    report['previous_materials']={key:cdo.get_editor_property(key).get_path_name() for key in ('mucus_material','mucus_core_material')}
    cdo.set_editor_property('mucus_material',materials[0]);cdo.set_editor_property('mucus_core_material',materials[1])
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,materials=[m.get_path_name() for m in materials],
        shared_materials_modified=False,new_textures=0,film_pool_capacity=16,film_lifetime_seconds=.4,
        user_testing_pending=True)
    record();print('M14_V09_VENOM_ASSETS_SAVED')

try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
