"""Create/save the shared fibre shader, two string finishes and two UI textures."""
from pathlib import Path
import json
import unreal as u

P=Path(__file__).parent
series=json.loads((P/'series.json').read_text(encoding='utf8'))
DEST=series['asset_directory']; ICONS='/Game/ColdSteelData/AttachmentIcons20260913'
E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary; A=u.AssetToolsHelpers.get_asset_tools()
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE active: end play before saving assets; current game preserved')
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text(encoding='utf8')) if receipt.exists() else {'saved':{},'gameplay_tested':False}
targets={ICONS+'/bow_dark_string_'+row['id'] for row in series['variants']}
repair_own_master=globals().get('_repair_own_master',False)
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
       if p.get_name().startswith(DEST+'/') or p.get_name() in targets]
if any(p!=DEST+'/M_BowString_Fiber' or not repair_own_master for p in dirty):
    raise RuntimeError('Preserve unsaved target packages '+str(dirty))

def existing(name,folder):
    if name in r['saved']:return u.load_asset(r['saved'][name])
    if E.does_asset_exist(folder+'/'+name):raise RuntimeError('Unowned target asset '+folder+'/'+name)
    return None

def save(asset):
    if not asset or not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed '+str(asset))
    r['saved'][asset.get_name()]=asset.get_path_name()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf8')
    print('BOW_STRING_SAVED',asset.get_path_name(),flush=True)

def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n

def wire(src,dst,pin,output=''):
    if not L.connect_material_expressions(src,output,dst,pin):raise RuntimeError('Connection failed '+pin)

def output(src,prop,channel=''):
    if not L.connect_material_property(src,channel,prop):raise RuntimeError('Material output failed '+str(prop))

name='M_BowString_Fiber'
master=u.load_asset(DEST+'/'+name) if repair_own_master else existing(name,DEST)
if not master or repair_own_master:
    if master:L.delete_all_material_expressions(master)
    else:master=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    inputs={}
    position=node(master,u.MaterialExpressionPreSkinnedPosition)
    scale=node(master,u.MaterialExpressionCustom,
        code='float3x3 m=GetLocalToWorld3x3(Parameters); return float3(length(m[0]),length(m[1]),length(m[2]));',
        description='Dynamic rod world scale',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    scale.set_editor_property('inputs',[])
    for key,value in [('P',position),('WorldScale',scale)]:
        vertex=node(master,u.MaterialExpressionVertexInterpolator)
        wire(value,vertex,'VS');inputs[key]=vertex
    for key,value in series['variants'][0]['surface'].items():
        if isinstance(value,list):
            inputs[key]=node(master,u.MaterialExpressionVectorParameter,parameter_name=key,default_value=u.LinearColor(*value,1))
        else:inputs[key]=node(master,u.MaterialExpressionScalarParameter,parameter_name=key,default_value=value)
    shader=node(master,u.MaterialExpressionCustom,code=(P/'Fiber.hlsl').read_text(),
                description='Physical pitch, filtered twisted fibre / cross braid',output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    shader.set_editor_property('inputs',pins)
    for key,value in inputs.items():wire(value,shader,key,'RGB' if key in ('Dark','Light','Tracer') else '')
    rgb=node(master,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);wire(shader,rgb,'')
    rough=node(master,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);wire(shader,rough,'')
    output(rgb,u.MaterialProperty.MP_BASE_COLOR);output(rough,u.MaterialProperty.MP_ROUGHNESS)
    output(node(master,u.MaterialExpressionConstant,r=0),u.MaterialProperty.MP_METALLIC)
    output(node(master,u.MaterialExpressionConstant,r=.35),u.MaterialProperty.MP_SPECULAR)
    errors=L.recompile_material(master)
    if errors:raise RuntimeError('Fibre material compile failed '+str(errors))
    E.set_metadata_tag(master,'Source','SourceAssets/BowStringVariants20260927/Fiber.hlsl')
    E.set_metadata_tag(master,'Geometry','Existing dynamic engine cylinder; radius 0.09 cm; no new mesh')
    save(master)

for row in series['variants']:
    material=existing(row['material'],DEST)
    if not material:
        material=A.create_asset(row['material'],DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(material,master)
        for key,value in row['surface'].items():
            if isinstance(value,list):L.set_material_instance_vector_parameter_value(material,key,u.LinearColor(*value,1))
            else:L.set_material_instance_scalar_parameter_value(material,key,value)
        L.update_material_instance(material);save(material)
    icon='bow_dark_string_'+row['id']
    if not existing(icon,ICONS):
        task=u.AssetImportTask();task.filename=str(P/'Icons'/(icon+'.png'))
        task.destination_path=ICONS;task.destination_name=icon;task.automated=True
        task.replace_existing=False;task.save=False;A.import_asset_tasks([task])
        texture=u.load_asset(ICONS+'/'+icon)
        if not texture:raise RuntimeError('Icon import failed '+icon)
        texture.srgb=True;texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
        texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI;texture.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
        save(texture)
print('BOW_STRING_ASSETS_COMPLETE',len(r['saved']))
