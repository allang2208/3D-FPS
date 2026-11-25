"""Import the new mane only. The existing horse supplies the bind skeleton and leader pose."""
import sys
from pathlib import Path
import unreal as u
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent)]
from import_horses import DEST, fbx_options, import_file, save

def author(source):
    folder=DEST+'/ManeR17'
    u.EditorAssetLibrary.make_directory(folder)
    texture=import_file(source/'T_Warhorse_Mane.png','T_Warhorse_Mane',folder)
    texture.set_editor_property('srgb',True)
    texture.set_editor_property('do_scale_mips_for_alpha_coverage',True)
    texture.set_editor_property('alpha_coverage_thresholds',u.Vector4(0,0,0,.27))
    save(texture)
    lib=u.MaterialEditingLibrary; path=folder+'/M_Warhorse_Mane'
    mat=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset('M_Warhorse_Mane',folder,u.Material,u.MaterialFactoryNew())
    lib.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    mat.set_editor_property('opacity_mask_clip_value',.27)
    mat.set_editor_property('two_sided',True)
    lib.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
    def node(ctype):return lib.create_material_expression(mat,ctype)
    def plug(n,ch,prop):
        if not lib.connect_material_property(n,ch,prop): raise RuntimeError(str(prop))
    tx=node(u.MaterialExpressionTextureSample);tx.texture=texture
    plug(tx,'RGB',u.MaterialProperty.MP_BASE_COLOR);plug(tx,'A',u.MaterialProperty.MP_OPACITY_MASK)
    rough=node(u.MaterialExpressionConstant);rough.r=.76;plug(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    spec=node(u.MaterialExpressionConstant);spec.r=.19;plug(spec,'',u.MaterialProperty.MP_SPECULAR)
    uv=node(u.MaterialExpressionTextureCoordinate)
    phase=node(u.MaterialExpressionTextureCoordinate);phase.coordinate_index=1
    bend=node(u.MaterialExpressionVectorParameter);bend.set_editor_property('parameter_name','ManeDisplacement')
    bend.set_editor_property('default_value',u.LinearColor(0,0,0,0))
    side=node(u.MaterialExpressionVectorParameter);side.set_editor_property('parameter_name','ManeSideAxis')
    side.set_editor_property('default_value',u.LinearColor(1,0,0,0))
    tm=node(u.MaterialExpressionTime)
    expr=node(u.MaterialExpressionCustom)
    expr.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    expr.set_editor_property('code',"""float tip=abs(Phase.y-0.5)>0.25?smoothstep(0.04,1.0,UV.y):0.0; float gust=sin(Clock*13.0+Phase.x*6.283)+0.32*sin(Clock*21.3+Phase.x*11.1);
float3 outward=Side*(Phase.y>0.5?1:-1); float3 drift=Bend-min(0,dot(Bend,outward))*outward;
return tip*tip*(drift*(1.0+0.14*gust)+float3(0,0,0.11*min(length(drift),5.0)*gust));""")
    slots=[]
    for key in ('UV','Phase','Bend','Side','Clock'):
        pin=u.CustomInput();pin.set_editor_property('input_name',key);slots.append(pin)
    expr.set_editor_property('inputs',slots)
    for n,key in ((uv,'UV'),(phase,'Phase'),(bend,'Bend'),(side,'Side'),(tm,'Clock')):
        if not lib.connect_material_expressions(n,'',expr,key):raise RuntimeError(key)
    plug(expr,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    lib.layout_material_expressions(mat);lib.recompile_material(mat);save(mat)
    skin=import_skin(source,folder,mat)
    return [obj.get_path_name() for obj in (texture,mat,skin)]

def import_skin(source,folder,mat):
    horse=u.load_asset(DEST+'/SK_StableWarhorse')
    options=fbx_options();options.skeleton=horse.skeleton;options.create_physics_asset=False
    skin=import_file(source/'SK_Warhorse_Mane.fbx','SK_Warhorse_Mane',folder,options)
    if skin.skeleton!=horse.skeleton:raise RuntimeError('Mane must follow the live horse skeleton')
    slots=list(skin.materials);slots[0].material_interface=mat;skin.materials=slots
    save(skin)
    return skin
