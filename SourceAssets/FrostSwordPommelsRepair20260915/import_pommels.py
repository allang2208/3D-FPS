"""Import the generated, fitted pommels and append only their runtime entries."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent;ROOT=P.parents[1]
D='/Game/Weapons/FrostCrystalSword20260915/PommelsRepair20260915'
F='/Game/Weapons/FrostCrystalSword20260915'
KEYS=['ballast_hardened','ballast_rune','ballast_magic_orb']
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;receipt=[]
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
def asset_task(source,name,folder,options=None):
    t=u.AssetImportTask();t.filename=str(source);t.destination_name=name;t.destination_path=folder
    t.automated=True;t.replace_existing=True;t.save=False
    if options:t.options=options
    A.import_asset_tasks([t]);asset=u.load_asset(folder+'/'+name)
    if not asset or not t.imported_object_paths:raise RuntimeError('Import failed: '+str(source))
    receipt.append({'source':str(source),'asset':asset.get_path_name()});return asset
def texture(file,name,folder,normal=False,icon=False,color=False):
    t=asset_task(file,name,folder);t.srgb=icon or color
    t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_EDITOR_ICON if icon else u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS
    if normal:t.flip_green_channel=True
    if icon:t.lod_group=u.TextureGroup.TEXTUREGROUP_UI;t.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    u.EditorAssetLibrary.save_loaded_asset(t,False);return t
def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(a,pin,b,field):
    if not L.connect_material_expressions(a,pin,b,field):raise RuntimeError('Material input '+field)
def material(key,normal,mask,base,orm,crystal=False):
    folder=D+'/'+key;name='M_FrostPommel_Crystal' if crystal else 'M_FrostPommel_Bronze'
    m=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
    if not crystal:
        n=node(m,u.MaterialExpressionTextureSample,texture=base,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);L.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        n=node(m,u.MaterialExpressionTextureSample,texture=orm,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS);L.connect_material_property(n,'G',u.MaterialProperty.MP_ROUGHNESS)
        n=node(m,u.MaterialExpressionConstant,r=.82);L.connect_material_property(n,'',u.MaterialProperty.MP_METALLIC)
    if not crystal:
        n=node(m,u.MaterialExpressionTextureSample,texture=normal,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL);L.connect_material_property(n,'RGB',u.MaterialProperty.MP_NORMAL)
    if crystal:
        m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        m.set_editor_property('two_sided',True)
        tint=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.0052,.3486,.5705,1));L.connect_material_property(tint,'',u.MaterialProperty.MP_BASE_COLOR)
        for value,prop in [(.62,u.MaterialProperty.MP_OPACITY),(.16,u.MaterialProperty.MP_ROUGHNESS),(0.,u.MaterialProperty.MP_METALLIC),(.35,u.MaterialProperty.MP_SPECULAR),(1.12,u.MaterialProperty.MP_REFRACTION)]:
            n=node(m,u.MaterialExpressionConstant,r=value);L.connect_material_property(n,'',prop)
        glow=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.00104,.06972,.1141,1));L.connect_material_property(glow,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    elif key=='ballast_rune':
        cover=node(m,u.MaterialExpressionTextureSample,texture=mask,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        color=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.82,.91,1,1))
        time=node(m,u.MaterialExpressionTime);sine=node(m,u.MaterialExpressionSine,period=2.6);link(time,'',sine,'')
        pulse=node(m,u.MaterialExpressionMultiply,const_b=.25);link(sine,'',pulse,'A')
        bias=node(m,u.MaterialExpressionAdd,const_b=1.6);link(pulse,'',bias,'A')
        strength=node(m,u.MaterialExpressionMultiply);link(cover,'R',strength,'A');link(bias,'',strength,'B')
        emission=node(m,u.MaterialExpressionMultiply);link(color,'',emission,'A');link(strength,'',emission,'B');L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.layout_material_expressions(m);L.recompile_material(m)
    u.EditorAssetLibrary.set_metadata_tag(m,'SurfaceSource','Corrected 5080 voxel export, welded/rebaked UV0; crystal uses blade blue with zero metallic and explicit translucent slot.')
    u.EditorAssetLibrary.save_loaded_asset(m,False);return m

def inlay_material(name,color,metallic,roughness,glow=False):
    m=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
    tint=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*color,1));L.connect_material_property(tint,'',u.MaterialProperty.MP_BASE_COLOR)
    for value,prop in [(metallic,u.MaterialProperty.MP_METALLIC),(roughness,u.MaterialProperty.MP_ROUGHNESS)]:
        n=node(m,u.MaterialExpressionConstant,r=value);L.connect_material_property(n,'',prop)
    if glow:
        time=node(m,u.MaterialExpressionTime);sine=node(m,u.MaterialExpressionSine,period=2.6);link(time,'',sine,'')
        pulse=node(m,u.MaterialExpressionMultiply,const_b=.20);link(sine,'',pulse,'A')
        bias=node(m,u.MaterialExpressionAdd,const_b=.65);link(pulse,'',bias,'A')
        emission=node(m,u.MaterialExpressionMultiply);link(tint,'',emission,'A');link(bias,'',emission,'B');L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.layout_material_expressions(m);L.recompile_material(m);u.EditorAssetLibrary.save_loaded_asset(m,False);return m

silver=inlay_material('M_FrostPommel_SilverInlay',(.75,.83,.90),.25,.24,True)
border=inlay_material('M_FrostPommel_InlayBorder',(.15,.070,.023),.82,.40)
collar=u.load_asset(F+'/GuardsSmooth20260915/M_FrostCrystalSword_SeamlessBronze')
catalog_path=ROOT/'Content/ColdSteelData/frost-sword-modules.json'
catalog=json.loads(catalog_path.read_text(encoding='utf-8-sig'));entries={}
for key in KEYS:
    folder=D+'/'+key;local=P/key
    normal=texture(local/'normal.png','T_Pommel_Normal',folder,normal=True)
    mask=texture(local/'rune_mask.png','T_Pommel_RuneMask',folder)
    base=texture(local/'base_color.png','T_Pommel_BaseColor',folder,color=True)
    orm=texture(local/'orm.png','T_Pommel_ORM',folder)
    bronze=material(key,normal,mask,base,orm)
    crystal=material(key,normal,mask,base,orm,True) if key=='ballast_magic_orb' else bronze
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    # Preserve the fitted surface normals, but build tangents from the final
    # mesh UVs in UE instead of importing Blender's per-layer tangent records.
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    name='SM_FrostPommel_'+key
    # Unattended FBX reimport replaces the task's data with the asset's saved
    # import data. Update that record too so the tangent policy takes effect.
    existing=u.load_asset(folder+'/'+name)
    if existing:
        saved=existing.get_editor_property('asset_import_data')
        saved.set_editor_property('normal_import_method',data.normal_import_method)
        saved.set_editor_property('normal_generation_method',data.normal_generation_method)
        saved.set_editor_property('vertex_color_import_option',data.vertex_color_import_option)
    mesh=asset_task(local/(name+'.fbx'),name,folder,opt)
    mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    build=mesh_editor.get_lod_build_settings(mesh,0)
    build.recompute_normals=False;build.recompute_tangents=True
    build.use_mikk_t_space=True;build.remove_degenerates=True
    build.use_full_precision_u_vs=True
    mesh_editor.set_lod_build_settings(mesh,0,build)
    for i,slot in enumerate(mesh.static_materials):
        source=str(slot.material_slot_name)
        mat=crystal if 'FrostPommel_Crystal' in source else bronze if 'FrostPommel_Bronze' in source else silver if 'SilverInlay' in source else border if 'InlayBorder' in source else collar if 'FrostPommel_Collar' in source else u.load_asset(F+'/M_FrostCrystalSword')
        mesh.set_material(i,mat)
    generation_receipt=(local/'receipt.json') if key!='ballast_hardened' else P.parent/'FrostSwordPommels5080_20260915'/key/'receipt.json'
    u.EditorAssetLibrary.set_metadata_tag(mesh,'Generation','TRELLIS.2-4B RTX 5080; '+json.loads(generation_receipt.read_text())['prompt_id'])
    u.EditorAssetLibrary.set_metadata_tag(mesh,'Mount','frost_hilt_v1: stock pommel rim, [0,0,-22.7] cm canonical mount; original collar retained.')
    u.EditorAssetLibrary.save_loaded_asset(mesh,False)
    entries[key]={'mesh':mesh.get_path_name(),'location_cm':catalog['slots']['pommel']['factory']['location_cm'],'interface':'frost_hilt_v1'}
    icon=local/'pommel_icon.png'
    if icon.exists():texture(icon,'ue_frost_crystal_sword_pommel_'+key,'/Game/ColdSteelData/AttachmentIcons20260913',icon=True)
catalog['slots']['pommel'].update(entries)
# Preserve unrelated slot edits made while the imports were running.
live=json.loads(catalog_path.read_text(encoding='utf-8-sig'));live['slots']['pommel'].update(entries)
catalog_path.write_text(json.dumps(live,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'import_receipt.json').write_text(json.dumps({'assets':receipt,'catalog_entries':entries,'testing':'not run'},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('FROST_POMMELS_IMPORTED')
