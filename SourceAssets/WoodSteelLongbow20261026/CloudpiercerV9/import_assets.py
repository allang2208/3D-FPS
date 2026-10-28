"""Save the Cloudpiercer's owned materials, skeletal body and framed UI texture."""
from pathlib import Path
import json, hashlib, shutil
import unreal as u

P=Path(__file__).parent
BASE='/Game/Weapons/WoodSteelLongbow20261026'
DEST=BASE+'/CloudpiercerV9'
ICON='/Game/ColdSteelData/AttachmentIcons20260913/FramedBows'
NAME='SK_HighlandLongbow_Cloudpiercer'
ICON_NAME='bow_woodsteel_riser_highland_cloudpiercer'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
author=json.loads((P/'authoring.json').read_text(encoding='utf-8'))
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else {'saved':{},'sources':{},'gameplay_tested':False}
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(DEST+'/') or package.get_name()==ICON+'/'+ICON_NAME:
        raise RuntimeError('Preserving unsaved package '+package.get_name())

def save(asset,source=None):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Package save failed '+str(asset))
    r['saved'][asset.get_name()]=asset.get_path_name()
    if source:r['sources'][asset.get_name()]=hashlib.sha256(source.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
    print('CLOUDPIERCER_SAVED '+asset.get_path_name(),flush=True)
def existing(name,folder=DEST):
    if name in r['saved']:return u.load_asset(r['saved'][name])
    if E.does_asset_exist(folder+'/'+name):raise RuntimeError('Preserving existing asset without this batch receipt '+folder+'/'+name)
    return None
def node(material,cls,**props):
    n=L.create_material_expression(material,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n
def connect(a,pin,b,slot):
    if not L.connect_material_expressions(a,pin,b,slot):raise RuntimeError('Material connection failed: '+slot)
def output(n,pin,property):
    if not L.connect_material_property(n,pin,property):raise RuntimeError('Material output failed: '+str(property))

materials={'M_WoodSteelLongbow_Steel':u.load_asset(BASE+'/M_WoodSteelLongbow_Steel')}
name='M_Cloudpiercer_Walnut';wood=existing(name)
if not wood:
    wood=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    parent=u.load_asset(BASE+'/M_WoodSteelLongbow_PBR')
    wood.set_editor_property('two_sided',parent.get_editor_property('two_sided'))
    samples={}
    for kind,sampler in [('BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('MetalRough',u.MaterialSamplerType.SAMPLERTYPE_MASKS),('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)]:
        texture=u.load_asset(BASE+'/Textures/T_WoodSteelLongbow_'+kind)
        if not texture:raise RuntimeError('Missing shared texture '+kind)
        samples[kind]=node(wood,u.MaterialExpressionTextureSample,texture=texture,sampler_type=sampler)
    tint=node(wood,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*author['walnut_tint'],1))
    tinted=node(wood,u.MaterialExpressionMultiply);connect(samples['BaseColor'],'RGB',tinted,'A');connect(tint,'',tinted,'B')
    nonmetal=node(wood,u.MaterialExpressionSubtract)
    connect(node(wood,u.MaterialExpressionConstant,r=1.0),'',nonmetal,'A');connect(samples['MetalRough'],'B',nonmetal,'B')
    vertex=node(wood,u.MaterialExpressionVertexColor)
    mask=node(wood,u.MaterialExpressionMultiply);connect(vertex,'R',mask,'A');connect(nonmetal,'',mask,'B')
    blend=node(wood,u.MaterialExpressionLinearInterpolate)
    connect(samples['BaseColor'],'RGB',blend,'A');connect(tinted,'',blend,'B');connect(mask,'',blend,'Alpha')
    output(blend,'',u.MaterialProperty.MP_BASE_COLOR)
    output(samples['MetalRough'],'G',u.MaterialProperty.MP_ROUGHNESS)
    output(samples['MetalRough'],'B',u.MaterialProperty.MP_METALLIC)
    output(samples['Normal'],'RGB',u.MaterialProperty.MP_NORMAL)
    L.set_material_usage(wood,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.recompile_material(wood);save(wood)
materials[name]=wood
for name,finish in author['finishes'].items():
    material=existing(name)
    if not material:
        material=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
        output(node(material,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*finish['color'],1)),'',u.MaterialProperty.MP_BASE_COLOR)
        output(node(material,u.MaterialExpressionConstant,r=finish['metallic']),'',u.MaterialProperty.MP_METALLIC)
        output(node(material,u.MaterialExpressionConstant,r=finish['roughness']),'',u.MaterialProperty.MP_ROUGHNESS)
        L.set_material_usage(material,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.recompile_material(material);save(material)
    materials[name]=material

source=P/'Export'/(NAME+'.fbx');mesh=existing(NAME)
if not mesh:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_mesh=True;options.import_as_skeletal=True;options.import_animations=False
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
    options.skeleton=u.load_asset(BASE+'/SK_WoodSteelLongbow_Original_Skeleton')
    if not options.skeleton:raise RuntimeError('Existing longbow skeleton is unavailable')
    d=options.skeletal_mesh_import_data
    d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False)
    d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=NAME
    task.automated=True;task.save=False;task.options=options
    A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+NAME)
    if not mesh:raise RuntimeError('Cloudpiercer skeletal mesh import failed')
    slots=list(mesh.get_editor_property('materials'))
    for index,slot in enumerate(slots):
        name=str(slot.material_slot_name)
        if name not in materials or not materials[name]:raise RuntimeError('Unresolved finish '+name)
        slot.set_editor_property('material_interface',materials[name]);slots[index]=slot
    mesh.set_editor_property('materials',slots);save(mesh,source)
    r['skeleton']=mesh.skeleton.get_path_name()
    r['materials']=[str(s.material_interface.get_path_name()) for s in slots]

texture=existing(ICON_NAME,ICON)
if not texture:
    png=P/(ICON_NAME+'.png')
    target=Path('D:/FPS3D/FPSGAME/Content')/ICON.removeprefix('/Game/')/(ICON_NAME+'.png')
    if target.exists():raise RuntimeError('Preserving existing icon source without a batch receipt '+str(target))
    shutil.copy2(png,target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_path=ICON;task.destination_name=ICON_NAME
    task.automated=True;task.save=False;task.factory=u.TextureFactory()
    A.import_asset_tasks([task]);texture=u.load_asset(ICON+'/'+ICON_NAME)
    if not texture:raise RuntimeError('Cloudpiercer icon import failed')
    texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI;texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    texture.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;texture.srgb=True;texture.max_texture_size=1024
    texture.set_editor_property('never_stream',True);save(texture,png)
r['complete']=True
receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
print('CLOUDPIERCER_IMPORT_COMPLETE',flush=True)
