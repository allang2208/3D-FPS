"""Build and save the scoped screen-space contour material."""
import unreal as u
from pathlib import Path

def build_outline(root,base):
    E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
    path=base+'/Materials/M_Staff_ContainerOutline_V1'
    mat=u.load_asset(path)
    if mat:return mat
    folder,name=path.rsplit('/',1);E.make_directory(folder)
    mat=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_POST_PROCESS)
    mat.set_editor_property('blendable_location',u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    mat.set_editor_property('blendable_priority',30)
    expressions=[]
    for index,(pin,scene_id) in enumerate((('ColorInput',u.SceneTextureId.PPI_POST_PROCESS_INPUT0),
        ('StencilInput',u.SceneTextureId.PPI_CUSTOM_STENCIL),('DepthInput',u.SceneTextureId.PPI_CUSTOM_DEPTH),
        ('SceneDepthInput',u.SceneTextureId.PPI_SCENE_DEPTH))):
        node=M.create_material_expression(mat,u.MaterialExpressionSceneTexture,-700,index*120)
        node.set_editor_property('scene_texture_id',scene_id);expressions.append((pin,node))
    for index,(pin,color) in enumerate((('Green',u.LinearColor(.08,1,.19,1)),('Yellow',u.LinearColor(1,.77,.055,1)))):
        node=M.create_material_expression(mat,u.MaterialExpressionVectorParameter,-700,520+index*120)
        node.set_editor_property('parameter_name',pin);node.set_editor_property('default_value',color);expressions.append((pin,node))
    node=M.create_material_expression(mat,u.MaterialExpressionScalarParameter,-700,790)
    node.set_editor_property('parameter_name','Width');node.set_editor_property('default_value',1.6);expressions.append(('Width',node))
    custom=M.create_material_expression(mat,u.MaterialExpressionCustom,-220,0)
    custom.set_editor_property('code',(root/'SearchContainersV1/container_outline.hlsl').read_text('utf8'))
    custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    custom.set_editor_property('description','Visible cabinet contour: unsearched green 201, searched yellow 202')
    inputs=[]
    for pin,node in expressions:
        item=u.CustomInput();item.set_editor_property('input_name',pin);inputs.append(item)
    custom.set_editor_property('inputs',inputs)
    for pin,node in expressions:
        if not M.connect_material_expressions(node,'',custom,pin):raise RuntimeError('Outline pin failed '+pin)
    M.connect_material_property(custom,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=M.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    M.get_statistics(mat) # finish required shader compilation, not a test/render
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Outline save failed')
    return mat
