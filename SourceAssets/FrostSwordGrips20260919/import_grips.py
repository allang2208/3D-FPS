"""Import grip assets and bind their existing modification IDs. No play/test."""
import unreal as u,json,shutil
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
D='/Game/Weapons/FrostCrystalSword20260915/Grips20260919'
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
receipts=[]
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
def task(file,name,folder,options=None):
    t=u.AssetImportTask();t.filename=str(file);t.destination_name=name;t.destination_path=folder;t.automated=True;t.replace_existing=True;t.save=False
    if options:t.options=options
    A.import_asset_tasks([t]);asset=u.load_asset(folder+'/'+name)
    if not asset or not t.imported_object_paths:raise RuntimeError('Import failed: '+str(file))
    receipts.append({'source':str(file),'asset':asset.get_path_name()});return asset
def texture(file,name,normal=False,color=False,icon=False,folder=D):
    t=task(file,name,folder);t.srgb=color or icon
    t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_EDITOR_ICON if icon else u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS
    if normal:t.flip_green_channel=True
    if icon:t.lod_group=u.TextureGroup.TEXTUREGROUP_UI;t.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    E.save_loaded_asset(t,False);return t
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def connect(n,pin,m,prop):
    if not L.connect_material_property(n,pin,prop):raise RuntimeError('Could not connect material property '+str(prop))
def new_mat(name):
    m=u.load_asset(D+'/'+name)
    if m:
        if E.get_metadata_tag(m,'FrostGrip.MaterialRevision')=='20260919':return m,False
        raise RuntimeError('Existing material is not owned by this completed import: '+name)
    return A.create_asset(name,D,u.Material,u.MaterialFactoryNew()),True
def finish(m):
    L.layout_material_expressions(m);L.recompile_material(m);E.set_metadata_tag(m,'FrostGrip.MaterialRevision','20260919');E.save_loaded_asset(m,False)
base=texture(P/'Textures/base_color.png','T_GripLeather_BaseColor',color=True)
normal=texture(P/'Textures/normal.png','T_GripLeather_Normal',normal=True)
rough=texture(P/'Textures/roughness.png','T_GripLeather_Roughness')
leather,create=new_mat('M_FrostGrip_Leather')
if create:
    for tex,sampler,prop,pin in [(base,u.MaterialSamplerType.SAMPLERTYPE_COLOR,u.MaterialProperty.MP_BASE_COLOR,'RGB'),(normal,u.MaterialSamplerType.SAMPLERTYPE_NORMAL,u.MaterialProperty.MP_NORMAL,'RGB'),(rough,u.MaterialSamplerType.SAMPLERTYPE_MASKS,u.MaterialProperty.MP_ROUGHNESS,'R')]:
        n=node(leather,u.MaterialExpressionTextureSample,texture=tex,sampler_type=sampler);connect(n,pin,leather,prop)
    n=node(leather,u.MaterialExpressionConstant,r=0.);connect(n,'',leather,u.MaterialProperty.MP_METALLIC)
    finish(leather)
silver,create=new_mat('M_FrostGrip_Silver')
if create:
    n=node(silver,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.48,.55,.62,1));connect(n,'',silver,u.MaterialProperty.MP_BASE_COLOR)
    for value,prop in [(.85,u.MaterialProperty.MP_METALLIC),(.32,u.MaterialProperty.MP_ROUGHNESS)]:
        n=node(silver,u.MaterialExpressionConstant,r=value);connect(n,'',silver,prop)
    finish(silver)
collar=u.load_asset('/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915/M_FrostCrystalSword_SeamlessBronze')
if not collar:raise RuntimeError('Original shared collar material is missing')
catalog_path=ROOT/'Content/ColdSteelData/frost-sword-modules.json'
if not (P/'Before'/catalog_path.name).exists():shutil.copy2(catalog_path,P/'Before'/catalog_path.name)
catalog=json.loads(catalog_path.read_text(encoding='utf-8-sig'));entries={}
animation_receipts=json.loads((P/'animation_receipt.json').read_text())
if len(animation_receipts)!=14:raise RuntimeError('Long-grip animation authoring has not finished')
for row in json.loads((P/'models.json').read_text()):
    key=row['id'];name=row['mesh'];folder=D+'/'+key
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    mesh=task(P/key/(name+'.fbx'),name,folder,opt)
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    build=editor.get_lod_build_settings(mesh,0);build.recompute_normals=False;build.recompute_tangents=True;build.use_mikk_t_space=True;build.remove_degenerates=True;build.use_full_precision_u_vs=True;editor.set_lod_build_settings(mesh,0,build)
    for i,slot in enumerate(mesh.static_materials):
        n=str(slot.material_slot_name);mesh.set_material(i,leather if 'Grip_Leather' in n else silver if 'Grip_Silver' in n else collar)
    E.set_metadata_tag(mesh,'FrostGrip.Source','Blender precision loft, original frost_hilt_v1 mounting rims, 20260919')
    E.set_metadata_tag(mesh,'FrostGrip.LengthCM',str(row['length_cm']))
    E.save_loaded_asset(mesh,False)
    icon=P/key/'grip_icon.png'
    texture(icon,'ue_frost_crystal_sword_grip_'+key,icon=True,folder='/Game/ColdSteelData/AttachmentIcons20260913')
    entries[key]={'mesh':mesh.get_path_name(),'location_cm':catalog['slots']['grip']['factory']['location_cm'],'interface':'frost_hilt_v1','pommel_offset_cm':row['pommel_offset_cm']}
    if key=='long_twohand':entries[key]['animation_folder']=D+'/LongGripAnimations'
# Read current file at commit time so unrelated parallel slots are retained.
live=json.loads(catalog_path.read_text(encoding='utf-8-sig'));live['slots']['grip'].update(entries)
catalog_path.write_text(json.dumps(live,ensure_ascii=False,indent=2),encoding='utf-8')
descriptions=ROOT/'Content/ColdSteelData/melee-gunsmith.json'
if not (P/'Before'/descriptions.name).exists():shutil.copy2(descriptions,P/'Before'/descriptions.name)
text=descriptions.read_text(encoding='utf-8-sig')
text=text.replace('双手接触的握柄区域。保留当前握柄材质、尺寸及双手握点，沿用现有握持、装备和检视动作。','双手接触的握柄区域。寒晶·双手剑可更换吸震缠柄、速握轻柄和长柄双手；长柄同步下移配重锤并适配左手握持。')
descriptions.write_text(text,encoding='utf-8')
(P/'import_receipt.json').write_text(json.dumps({'assets':receipts,'catalog_entries':entries,'testing':'not run; user will test'},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('FROST_GRIPS_IMPORTED')
