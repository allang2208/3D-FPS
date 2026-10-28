"""Import and save the owned Peakwatch optics, finishes and catalog icon."""
from pathlib import Path
import json, hashlib, shutil, importlib.util
import unreal as u

P=Path(__file__).parent
ROOT=Path('D:/FPS3D/FPSGAME')
DEST='/Game/Weapons/WoodSteelLongbow20261026/Scope3to6V11'
ICON='/Game/ColdSteelData/AttachmentIcons20260913/FramedBows'
ICON_NAME='bow_woodsteel_sight_highland_peakwatch_3_6x'
SHARED='/Game/Weapons/DarkBow20260925/SingleLensOptics20260927/Textures'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
author=json.loads((P/'authoring.json').read_text(encoding='utf-8'))
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else {'saved':{},'sources':{},'gameplay_tested':False}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE active: preserve the running session')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(DEST+'/') or package.get_name()==ICON+'/'+ICON_NAME:
        raise RuntimeError('Preserving unsaved package '+package.get_name())

def save(asset,source=None):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Package save failed '+str(asset))
    r['saved'][asset.get_name()]=asset.get_path_name()
    if source:r['sources'][asset.get_name()]=hashlib.sha256(source.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
    print('PEAKWATCH_SAVED '+asset.get_path_name(),flush=True)

def existing(name,folder=DEST):
    if name in r['saved']:return u.load_asset(r['saved'][name])
    if E.does_asset_exist(folder+'/'+name):raise RuntimeError('Preserving unowned asset '+folder+'/'+name)
    return None

def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n

def wire(a,pin,b,slot):
    if not L.connect_material_expressions(a,pin,b,slot):raise RuntimeError('Material connection failed '+slot)

def output(n,pin,prop):
    if not L.connect_material_property(n,pin,prop):raise RuntimeError('Material output failed '+str(prop))

def scalar(m,value):return node(m,u.MaterialExpressionConstant,r=value)
def color(m,value):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1))

wood_name='T_Peakwatch_WalnutBaseColor';wood_texture=existing(wood_name,DEST+'/Textures')
if not wood_texture:
    source=P/'Textures'/(wood_name+'.png')
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST+'/Textures';task.destination_name=wood_name
    task.automated=True;task.save=False;task.factory=u.TextureFactory();A.import_asset_tasks([task])
    wood_texture=u.load_asset(DEST+'/Textures/'+wood_name)
    if not wood_texture:raise RuntimeError('Walnut color import failed')
    wood_texture.srgb=True;wood_texture.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    wood_texture.compression_settings=u.TextureCompressionSettings.TC_DEFAULT
    wood_texture.max_texture_size=1024;save(wood_texture,source)

orm=u.load_asset(SHARED+'/T_BowOptic_MetalORM');normal=u.load_asset(SHARED+'/T_BowOptic_MetalNormal')
if not orm or not normal:raise RuntimeError('Shared machined metal textures are unavailable')
finishes={
 'M_Peakwatch_Steel':((.40,.46,.48),.85,.30),
 'M_Peakwatch_DarkSteel':((.037,.050,.056),.70,.38),
 'M_Peakwatch_Brass':((.40,.25,.095),.80,.34),
 'M_Peakwatch_Engraving':((.018,.022,.021),0,.70),
 'M_Peakwatch_Walnut':((.14,.048,.022),0,.47)
}
materials={}
for name,(rgb,metallic,roughness) in finishes.items():
    m=existing(name)
    if not m:
        m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
        if name=='M_Peakwatch_Walnut':
            base=node(m,u.MaterialExpressionTextureSample,texture=wood_texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            output(base,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        else:output(color(m,rgb),'',u.MaterialProperty.MP_BASE_COLOR)
        output(scalar(m,metallic),'',u.MaterialProperty.MP_METALLIC)
        if metallic>0:
            sample=node(m,u.MaterialExpressionTextureSample,texture=orm,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            rough=node(m,u.MaterialExpressionMultiply,const_b=roughness/.34);wire(sample,'G',rough,'A')
            output(rough,'',u.MaterialProperty.MP_ROUGHNESS)
            bump=node(m,u.MaterialExpressionTextureSample,texture=normal,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            output(bump,'RGB',u.MaterialProperty.MP_NORMAL)
        else:output(scalar(m,roughness),'',u.MaterialProperty.MP_ROUGHNESS)
        L.recompile_material(m);save(m)
    materials[name]=m

name='M_Peakwatch_Glass';glass=existing(name)
if not glass:
    module_path=ROOT/'SourceAssets/BowSingleLensOptics20260927/ReticleReadability/materials.py'
    spec=importlib.util.spec_from_file_location('peakwatch_reticle',module_path)
    reticle=importlib.util.module_from_spec(spec);spec.loader.exec_module(reticle)
    glass=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    reticle.build_lens(glass,4)
    L.recompile_material(glass);save(glass)
materials[name]=glass

flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for row in author['assets']:
        name=row['mesh'];mesh=existing(name)
        if not mesh:
            source=P/'Export'/(name+'.fbx')
            opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
            opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
            d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.build_nanite=False
            d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
            task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=name
            task.automated=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
            mesh=u.load_asset(DEST+'/'+name)
            if not mesh:raise RuntimeError('Mesh import failed '+name)
            slots=list(mesh.get_editor_property('static_materials'))
            for index,slot in enumerate(slots):
                material_name=str(slot.material_slot_name)
                if material_name not in materials:raise RuntimeError('Unknown material slot '+material_name)
                slot.set_editor_property('material_interface',materials[material_name]);slots[index]=slot
            mesh.set_editor_property('static_materials',slots);save(mesh,source)
            r.setdefault('mesh_materials',{})[name]=[s.material_interface.get_path_name() for s in slots]
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))

texture=existing(ICON_NAME,ICON)
if not texture:
    png=P/(ICON_NAME+'.png')
    target=ROOT/'Content'/ICON.removeprefix('/Game/')/(ICON_NAME+'.png')
    if target.exists() and target.read_bytes()!=png.read_bytes():raise RuntimeError('Preserving existing icon source '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(png,target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_path=ICON;task.destination_name=ICON_NAME
    task.automated=True;task.save=False;task.factory=u.TextureFactory();A.import_asset_tasks([task])
    texture=u.load_asset(ICON+'/'+ICON_NAME)
    if not texture:raise RuntimeError('Peakwatch icon import failed')
    texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI;texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    texture.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;texture.srgb=True;texture.max_texture_size=1024
    texture.set_editor_property('never_stream',True);save(texture,png)
r['complete']=True
receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
print('PEAKWATCH_IMPORT_COMPLETE',flush=True)
