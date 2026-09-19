import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
D='/Game/Weapons/FrostCrystalSword20260915/Guards20260915'
F='/Game/Weapons/FrostCrystalSword20260915'
ICONS='/Game/ColdSteelData/AttachmentIcons20260913'
ids=['bastion_guard','riposte_guard','light_guard']
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
receipt=[]
def task(file,name,folder,options=None):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=folder;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False
    if options:t.options=options
    A.import_asset_tasks([t])
    asset=u.load_asset(folder+'/'+name)
    if not asset or not t.imported_object_paths:raise RuntimeError('Import failed: '+str(file))
    receipt.append({'source':str(file),'asset':asset.get_path_name()})
    return asset
def texture(file,name,folder,kind):
    t=task(file,name,folder)
    t.srgb=kind=='icon'
    if kind=='normal':
        t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP;t.flip_green_channel=True
    elif kind=='icon':
        t.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;t.lod_group=u.TextureGroup.TEXTUREGROUP_UI;t.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    else:t.compression_settings=u.TextureCompressionSettings.TC_MASKS
    u.EditorAssetLibrary.save_loaded_asset(t,False)
    return t
textures={}
for id in ids:
    folder=D+'/'+id
    textures[id]={kind:texture(P/id/(kind+'.png'),'T_Guard_'+id+'_'+kind,folder,kind) for kind in ['normal','ao']}
    texture(P/id/'guard_icon.png','ue_frost_crystal_sword_guard_'+id,ICONS,'icon')

material=u.load_asset(D+'/M_FrostGuard_Bronze') or A.create_asset('M_FrostGuard_Bronze',D,u.Material,u.MaterialFactoryNew())
E.delete_all_material_expressions(material)
E.set_material_usage(material,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
def node(cls,**props):
    n=E.create_material_expression(material,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
uv=json.loads((P/'mount_source.json').read_text())['material_sample_uv']
surface_uv=node(u.MaterialExpressionTextureCoordinate,coordinate_index=1)
detail_uv=node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
for label,prop,sampler,channel in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR,u.MaterialSamplerType.SAMPLERTYPE_COLOR,'RGB'),('Metallic',u.MaterialProperty.MP_METALLIC,u.MaterialSamplerType.SAMPLERTYPE_MASKS,'R'),('Roughness',u.MaterialProperty.MP_ROUGHNESS,u.MaterialSamplerType.SAMPLERTYPE_MASKS,'R')]:
    tex=u.load_asset(F+'/T_FrostCrystalSword_'+label)
    n=node(u.MaterialExpressionTextureSample,texture=tex,sampler_type=sampler)
    E.connect_material_expressions(surface_uv,'',n,'UVs');E.connect_material_property(n,channel,prop)
for kind,prop,sampler in [('normal',u.MaterialProperty.MP_NORMAL,u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('ao',u.MaterialProperty.MP_AMBIENT_OCCLUSION,u.MaterialSamplerType.SAMPLERTYPE_MASKS)]:
    n=node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='Guard_'+kind,texture=textures[ids[0]][kind],sampler_type=sampler)
    E.connect_material_expressions(detail_uv,'',n,'UVs')
    E.connect_material_property(n,'RGB' if kind=='normal' else 'R',prop)
E.layout_material_expressions(material);E.recompile_material(material)
u.EditorAssetLibrary.save_loaded_asset(material,False)
donor=u.load_asset(F+'/SK_FrostCrystalSword_Manny')
bindings={str(slot.material_slot_name):slot.material_interface for slot in donor.get_editor_property('materials')}
for id in ids:
    folder=D+'/'+id
    mi=u.load_asset(folder+'/MI_Guard_Bronze') or A.create_asset('MI_Guard_Bronze',folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    E.set_material_instance_parent(mi,material)
    for kind,tex in textures[id].items():E.set_material_instance_texture_parameter_value(mi,'Guard_'+kind,tex)
    u.EditorAssetLibrary.set_metadata_tag(mi,'FinishReference',F+'/M_FrostCrystalSword; UV1 transferred from original bronze quillons; UV0 baked normal/AO and tangents')
    u.EditorAssetLibrary.save_loaded_asset(mi,False)
    own=dict(bindings);own['M_FrostGuard_Bronze_'+id]=mi
    own['M_FrostCrystalSword']=u.load_asset(F+'/M_FrostCrystalSword')
    for name in ['SM_Guard_'+id,'SM_FrostCrystalSword_'+id]:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
        opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
        opt.static_mesh_import_data.generate_lightmap_u_vs=False
        opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        mesh=task(P/id/(name+'.fbx'),name,folder,opt)
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            source=str(slot.material_slot_name)
            if source not in own:raise RuntimeError('Unmapped static material: '+source)
            mesh.set_material(i,own[source])
        u.EditorAssetLibrary.save_loaded_asset(mesh,False)
    name='SK_FrostCrystalSword_'+id
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    opt.skeleton=donor.skeleton
    opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=task(P/id/(name+'.fbx'),name,folder,opt)
    slots=mesh.get_editor_property('materials')
    for i,slot in enumerate(slots):
        source=str(slot.material_slot_name)
        if source not in own:raise RuntimeError('Unmapped skeletal material: '+source)
        slot.material_interface=own[source];slots[i]=slot
    mesh.set_editor_property('materials',slots)
    mesh.set_editor_property('positive_bounds_extension',u.Vector(120,120,120));mesh.set_editor_property('negative_bounds_extension',u.Vector(120,120,120))
    u.EditorAssetLibrary.save_loaded_asset(mesh,False)
(P/'import_receipt.json').write_text(json.dumps({'assets':receipt,'material':material.get_path_name(),'skeleton':donor.skeleton.get_path_name(),'testing':'Not run'},indent=2))
u.log('FROST_GUARDS_IMPORTED')
