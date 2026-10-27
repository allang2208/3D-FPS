"""Create/save Illumination Arrow materials and its authored icon; no play/render tests."""
from pathlib import Path
import json
import unreal as u
R=Path(__file__).resolve().parents[2]
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
BASE='/Game/Skills/IlluminationArrow20261027'
E.make_directory(BASE)
saved=[]
def material(name):
    path=BASE+'/'+name
    # Reruns preserve previously saved production assets.
    existing=u.load_asset(path)
    if existing:return existing,False
    return u.AssetToolsHelpers.get_asset_tools().create_asset(name,BASE,u.Material,u.MaterialFactoryNew()),True
def node(mat,cls,**props):
    result=M.create_material_expression(mat,cls)
    for key,value in props.items():result.set_editor_property(key,value)
    return result
def custom(mat,code,inputs,output):
    c=node(mat,u.MaterialExpressionCustom,code=code,output_type=output)
    pins=[]
    for name,source in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    c.set_editor_property('inputs',pins)
    for name,source in inputs:
        if not M.connect_material_expressions(source,'',c,name):raise RuntimeError('Could not connect '+name)
    return c
def finish(mat):
    errors=M.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    M.get_statistics(mat)  # Complete shader compilation required to save the new material.
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Save failed '+mat.get_path_name())
    saved.append(mat.get_path_name())

mat,new=material('M_IlluminationArrowGlow')
if new:
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True)
    uv=node(mat,u.MaterialExpressionTextureCoordinate)
    mask=custom(mat,'return pow(saturate(1-abs(UV.y*2-1)),1.2)*sin(saturate(UV.x)*3.14159265);',[('UV',uv)],u.CustomMaterialOutputType.CMOT_FLOAT1)
    color=node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(12,9.5,4.8,1))
    M.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    M.connect_material_property(mask,'',u.MaterialProperty.MP_OPACITY)
    finish(mat)
else:saved.append(mat.get_path_name())

mat,new=material('M_IlluminationMarkDepth')
if new:
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True)
    M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    finish(mat)
else:saved.append(mat.get_path_name())

mat,new=material('M_IlluminationMarkOutline')
if new:
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_POST_PROCESS)
    mat.set_editor_property('blendable_location',u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    mat.set_editor_property('blendable_priority',35)
    inputs=[(name,node(mat,u.MaterialExpressionSceneTexture,scene_texture_id=kind)) for name,kind in (
        ('ColorInput',u.SceneTextureId.PPI_POST_PROCESS_INPUT0),('StencilInput',u.SceneTextureId.PPI_CUSTOM_STENCIL))]
    code=(R/'SourceAssets/IlluminationArrow20261027/mark_outline.hlsl').read_text('utf-8')
    c=custom(mat,code,inputs,u.CustomMaterialOutputType.CMOT_FLOAT3)
    M.connect_material_property(c,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    finish(mat)
else:saved.append(mat.get_path_name())

name='illumination_arrow_cold_steel'
task=u.AssetImportTask();task.filename=str(R/'Content/ColdSteelData/Skills'/f'{name}.png')
task.destination_path='/Game/ColdSteelData/Skills';task.destination_name=name
task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(task.destination_path+'/'+name)
if not task.imported_object_paths or not isinstance(texture,u.Texture2D):raise RuntimeError('Icon import failed')
texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('never_stream',True);texture.set_editor_property('srgb',True);texture.set_editor_property('max_texture_size',512)
if not E.save_loaded_asset(texture,False):raise RuntimeError('Icon save failed')
saved.append(texture.get_path_name())
out=R/'Saved/IlluminationArrow20261027';out.mkdir(parents=True,exist_ok=True)
(out/'asset-receipt.json').write_text(json.dumps({'saved':saved,'runtime_tested':False},indent=2),encoding='utf-8')
print('ILLUMINATION_ARROW_ASSETS_SAVED '+str(len(saved)))
