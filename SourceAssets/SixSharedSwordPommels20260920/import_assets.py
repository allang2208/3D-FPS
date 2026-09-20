"""Import the reverse fitting, Rune silver finishes and six-option UI images."""
import unreal as u, json, shutil
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1];SRC=P.parent
D='/Game/Weapons/SixSharedSwordPommels20260920';F='/Game/Weapons/FrostCrystalSword20260915'
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor is None or editor.is_in_play_in_editor():raise RuntimeError('FPSGAME editor must be open outside PIE for this import batch.')
L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
fit=json.loads((P/'rune_fit.json').read_text());ids=fit['ids']
original=json.loads((SRC/'FrostSwordPommelsRepair20260915/import_receipt.json').read_text())['catalog_entries']
rune=json.loads((SRC/'RuneSwordPommels20260920/import_receipt.json').read_text())[0]
receipt={'finishes':{'silver':{}},'meshes':{},'materials':{},'icons':[]}
def save(asset):
    if not L.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
def node(mat,cls,**properties):
    n=M.create_material_expression(mat,cls)
    for k,v in properties.items():n.set_editor_property(k,v)
    return n
def link(a,output,b,pin):
    if not M.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect material pin '+pin)
def output(a,pin,prop):
    if not M.connect_material_property(a,pin,prop):raise RuntimeError('Cannot connect material output')
def silver_tint(mat,source,source_pin):
    gray=node(mat,u.MaterialExpressionDesaturation);one=node(mat,u.MaterialExpressionConstant,r=1.)
    link(source,source_pin,gray,'');link(one,'',gray,'Fraction')
    tint=node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*fit['silver_tint'],1))
    mul=node(mat,u.MaterialExpressionMultiply);link(gray,'',mul,'A');link(tint,'',mul,'B')
    clamp=node(mat,u.MaterialExpressionClamp,min_default=0.,max_default=1.);link(mul,'',clamp,'')
    return clamp
cache={}
for old,new in ids.items():
    mesh=u.load_asset(original[old]['mesh']);overrides={}
    if not mesh:raise RuntimeError('Missing original pommel: '+old)
    for slot in mesh.static_materials:
        source=slot.material_interface;label=source.get_name() if source else ''
        if not any(x in label for x in ['Bronze','InlayBorder']) and 'Collar' not in str(slot.material_slot_name):continue
        path=source.get_path_name()
        if path not in cache:
            suffix='Collar' if 'Collar' in str(slot.material_slot_name) else 'InlayBorder' if 'InlayBorder' in label else new
            target=D+'/Materials/M_SixPommel_RuneSilver_'+suffix
            material=u.load_asset(target) if L.does_asset_exist(target) else L.duplicate_asset(path,target)
            if not material:raise RuntimeError('Cannot duplicate finish material: '+path)
            if L.get_metadata_tag(material,'SixPommelSilverSource')!=path:
                base=M.get_material_property_input_node(material,u.MaterialProperty.MP_BASE_COLOR)
                if not base:raise RuntimeError('Original finish has no base color input: '+path)
                color=silver_tint(material,base,'RGB' if isinstance(base,u.MaterialExpressionTextureSample) else '')
                output(color,'',u.MaterialProperty.MP_BASE_COLOR);M.layout_material_expressions(material);M.recompile_material(material)
                L.set_metadata_tag(material,'SixPommelSilverSource',path);save(material)
            cache[path]=material.get_path_name();receipt['materials'][path]=cache[path]
        overrides[str(slot.material_slot_name)]=cache[path]
    receipt['finishes']['silver'][new]={'materials':overrides}
    receipt['meshes'][new]=mesh.get_path_name()
    print('SIX_POMMEL_SILVER_SAVED',new)

target=D+'/Materials/M_SixPommel_RuneToFrost'
mat=u.load_asset(target) if L.does_asset_exist(target) else A.create_asset('M_SixPommel_RuneToFrost',D+'/Materials',u.Material,u.MaterialFactoryNew())
M.delete_all_material_expressions(mat)
uv0=node(mat,u.MaterialExpressionTextureCoordinate,coordinate_index=0);uv1=node(mat,u.MaterialExpressionTextureCoordinate,coordinate_index=1)
vcol=node(mat,u.MaterialExpressionVertexColor)
for channel,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Metallic',u.MaterialProperty.MP_METALLIC),('Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
    sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
    a=node(mat,u.MaterialExpressionTextureSample,texture=u.load_asset(rune['textures'][channel]),sampler_type=sampler);link(uv0,'',a,'UVs')
    b=node(mat,u.MaterialExpressionTextureSample,texture=u.load_asset(F+'/T_FrostCrystalSword_'+channel),sampler_type=sampler);link(uv1,'',b,'UVs')
    lower=silver_tint(mat,b,'RGB') if channel=='BaseColor' else b
    mix=node(mat,u.MaterialExpressionLinearInterpolate);link(a,'RGB' if channel=='BaseColor' else 'R',mix,'A');link(lower,'' if channel=='BaseColor' else 'R',mix,'B');link(vcol,'R',mix,'Alpha');output(mix,'',prop)
a=node(mat,u.MaterialExpressionTextureSample,texture=u.load_asset(rune['textures']['Normal']),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL);link(uv0,'',a,'UVs')
flat=node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1,1));mix=node(mat,u.MaterialExpressionLinearInterpolate)
link(a,'RGB',mix,'A');link(flat,'',mix,'B');link(vcol,'R',mix,'Alpha');output(mix,'',u.MaterialProperty.MP_NORMAL)
M.layout_material_expressions(mat);M.recompile_material(mat);save(mat)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
task=u.AssetImportTask();task.filename=str(P/'Export/SM_SwordPommel_RuneToFrost.fbx');task.destination_path=D+'/Interfaces';task.destination_name='SM_SwordPommel_RuneToFrost';task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
A.import_asset_tasks([task]);adapter=u.load_asset(D+'/Interfaces/SM_SwordPommel_RuneToFrost')
if not adapter or not task.imported_object_paths:raise RuntimeError('Reverse interface import failed')
for i in range(len(adapter.static_materials)):adapter.set_material(i,mat)
save(adapter);receipt['adapter']=adapter.get_path_name();receipt['adapter_material']=mat.get_path_name()
icons=ROOT/'Content/ColdSteelData/AttachmentIcons20260913';backup=P/'BeforeSix';backup.mkdir(exist_ok=True)
copies=[]
for old,new in ids.items():
    native=SRC/'FrostSwordPommelsRepair20260915'/old/'pommel_icon.png'
    copies.extend([(P/'Icons'/('ue_rune_sword_pommel_'+new+'.png'),'ue_rune_sword_pommel_'+new),
                   (native,'ue_frost_crystal_sword_pommel_'+new),(native,'pommel_'+new)])
for key in ids:
    copies.append((SRC/'RuneSwordPommels20260920/Icons'/('ue_rune_sword_pommel_'+key+'.png'),'pommel_'+key))
for source,name in copies:
    target=icons/(name+'.png')
    for prior in [target,target.with_suffix('.uasset')]:
        if prior.exists() and not (backup/prior.name).exists():shutil.copy2(prior,backup/prior.name)
    shutil.copy2(source,target)
    path='/Game/ColdSteelData/AttachmentIcons20260913/'+name
    result=u.ModelingService.import_texture(str(target),path,True,'Default',True)
    if not result.success:raise RuntimeError(result.message)
    texture=u.load_asset(path);texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI;texture.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    save(texture);receipt['icons'].append({'source':str(source),'asset':texture.get_path_name()})
receipt['tests_run']=False
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('SIX_SHARED_POMMEL_ASSETS_SAVED',len(receipt['icons']))
