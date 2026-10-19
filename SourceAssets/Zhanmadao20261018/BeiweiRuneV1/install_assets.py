"""Save Beiwei textures, seven native blade materials and their temporal variants."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/Zhanmadao20261018/BeiweiRuneV1'
E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=P/'AssetHost':raise RuntimeError('Use the isolated asset host')
sources=json.loads((P/'source_bindings.json').read_text(encoding='utf-8'))
layouts=json.loads((P.parent/'RuneSurfaceV1/layouts.json').read_text(encoding='utf-8'))
receipt={'assets':[],'bindings':{},'temporal_bindings':{},'assets_saved':False,'staged_assets_saved':False,'complete':False,'game_tested':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(asset):
    if isinstance(asset,u.Material):
        errors=E.recompile_material(asset)
        if errors:raise RuntimeError(str(errors))
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());record()
def texture(file,path,icon=False):
    folder,name=path.rsplit('/',1)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory()
    A.import_asset_tasks([task]);asset=u.load_asset(path)
    if not asset:raise RuntimeError('Texture import failed '+path)
    props=dict(srgb=icon,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON if icon else u.TextureCompressionSettings.TC_GRAYSCALE,
        address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,max_texture_size=1024 if icon else 2048)
    if icon:props.update(lod_group=u.TextureGroup.TEXTUREGROUP_UI,never_stream=True,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    else:props.update(never_stream=False,power_of_two_mode=u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
    asset.set_editor_properties(props);save(asset);return asset
mask=texture(P/'Artwork/Beiwei_Blade_Mask.png',D+'/Textures/T_Mask_beiwei_rune')
texture(P/'Artwork/Beiwei_Icon_V1.png','/Game/ColdSteelData/AttachmentIcons20260913/ue_zhanmadao_blade_2_beiwei_rune',True)
for choice,materials in sources.items():
    receipt['bindings'][choice]={}
    layout=layouts[choice];z=layout['z_cm'];width=layout['rune_width_cm'][len(z)//2]
    branch=(P/'beiwei_emission.hlsl').read_text(encoding='utf-8').replace('BEIWEI_WIDTH_CM',format(width,'.8f')).replace('BEIWEI_CENTER_CM',format(z[0]+(z[-1]-z[0])*.52,'.8f'))
    for index,(slot,source_path) in enumerate(materials.items()):
        name='M_TangDaoBladeRuneSurface_Zhanmadao_'+choice+'_'+str(index)+'_BeiweiV1'
        paths=[]
        for temporal in [False,True]:
            source=source_path.split('.')[0]+('_Whirlwind' if temporal else '')
            target=D+'/Materials/'+name+('_Whirlwind' if temporal else '')
            asset=u.load_asset(target) or L.duplicate_asset(source,target)
            if not asset:raise RuntimeError('Missing source '+source)
            changed=False
            for node in E.get_material_expressions(asset):
                if not isinstance(node,u.MaterialExpressionCustom):continue
                code=node.get_editor_property('code');marker='// END_ZHANMADAO_BLADE_CONTOUR_V1'
                if marker not in code:continue
                if 'BEIWEI_RUNE_V1' not in code:
                    code='float3 BeiweiRawP=P.xyz;\n'+code.replace(marker,marker+'\n'+branch,1)
                    node.set_editor_property('code',code)
                changed=True
            if not changed:raise RuntimeError('Missing contour node '+source)
            L.set_metadata_tag(asset,'BeiweiRuneRevision','BeiweiRuneV1');save(asset);paths.append(asset.get_path_name())
        receipt['bindings'][choice][slot]=paths[0];receipt['temporal_bindings'][paths[0]]=paths[1]
name='M_BeiweiSwordTrail';path=D+'/Materials/'+name
material=u.load_asset(path) or A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
for node in list(E.get_material_expressions(material)):E.delete_material_expression(material,node)
material.set_editor_properties(dict(blend_mode=u.BlendMode.BLEND_TRANSLUCENT,shading_model=u.MaterialShadingModel.MSM_UNLIT,
    two_sided=True,disable_depth_test=False,translucency_pass=u.MaterialTranslucencyPass.MTP_BEFORE_DOF))
def node(cls,**props):
    n=E.create_material_expression(material,cls)
    if props:n.set_editor_properties(props)
    return n
def wire(a,b,pin=''):E.connect_material_expressions(a,'',b,pin)
uv=node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
custom=node(u.MaterialExpressionCustom,code=(P/'sword_trail.hlsl').read_text(encoding='utf-8'),output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
pin=u.CustomInput();pin.set_editor_property('input_name','UV');custom.set_editor_property('inputs',[pin]);wire(uv,custom,'UV')
rgb=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);alpha=node(u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
wire(custom,rgb);wire(custom,alpha)
exposure=node(u.MaterialExpressionEyeAdaptationInverse)
wire(rgb,exposure,E.get_material_expression_input_names(exposure)[0])
one=node(u.MaterialExpressionConstant,r=1.);wire(one,exposure,E.get_material_expression_input_names(exposure)[1])
E.connect_material_property(exposure,'',u.MaterialProperty.MP_EMISSIVE_COLOR);E.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
save(material)
receipt.update(staged_assets_saved=True,material_count=15,blade_choices=list(sources));record()
print('BEIWEI_ASSETS_STAGED',len(receipt['assets']),flush=True)
