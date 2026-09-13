"""Import M1911 refined surfaces on the accepted P9/Manny skeleton."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/M1911/Hero20260913';A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
reference=u.load_asset('/Game/Weapons/M1911/P9Retarget20260913/SK_M1911_Manny')
bindings={str(slot.material_slot_name):slot.material_interface for slot in reference.materials}
manifest=json.loads((O/'textures.json').read_text());materials={};receipt={'materials':{},'textures':{}}
def output(node,pin,prop):
    if not L.connect_material_property(node,pin,prop):raise RuntimeError('Cannot connect '+str(prop))
for group,info in manifest.items():
    name=info['material'];path=D+'/Materials/'+name
    m=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    maps={}
    for kind,filename in info['textures'].items():
        texname=Path(filename).stem;t=u.AssetImportTask();t.filename=filename;t.destination_path=D+'/Textures';t.destination_name=texname
        t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=u.load_asset(D+'/Textures/'+texname)
        if not tex:raise RuntimeError('Texture import failed: '+filename)
        tex.set_editor_property('srgb',kind=='BaseColor');tex.set_editor_property('lod_bias',0)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
        if not u.EditorAssetLibrary.save_loaded_asset(tex,False):raise RuntimeError('Texture save failed: '+texname)
        node=L.create_material_expression(m,u.MaterialExpressionTextureSample);node.set_editor_property('texture',tex)
        node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        if kind=='BaseColor':output(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        elif kind=='Normal':output(node,'RGB',u.MaterialProperty.MP_NORMAL)
        else:
            output(node,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION);output(node,'G',u.MaterialProperty.MP_ROUGHNESS);output(node,'B',u.MaterialProperty.MP_METALLIC)
        maps[kind]=tex.get_path_name()
    L.recompile_material(m)
    if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Material save failed: '+name)
    materials[name]=m;receipt['materials'][name]=m.get_path_name();receipt['textures'][group]=maps
    u.log('M1911_HERO_MATERIAL_IMPORTED '+group)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=reference.skeleton
data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
t=u.AssetImportTask();t.filename=str(O/'SK_M1911_Manny.fbx');t.destination_path=D;t.destination_name='SK_M1911_Manny';t.options=opt;t.automated=True;t.replace_existing=True;t.save=False
A.import_asset_tasks([t]);mesh=u.load_asset(D+'/SK_M1911_Manny')
if not mesh:raise RuntimeError('M1911 mesh import failed')
slots=mesh.materials
for i,slot in enumerate(slots):
    key=str(slot.material_slot_name);slot.material_interface=materials[key] if key in materials else bindings[key];slots[i]=slot
mesh.set_editor_property('materials',slots)
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('M1911 mesh save failed')
receipt.update({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'animations':'Existing P9Retarget20260913 clips retained without reimport','material_slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'state':'Imported; no rendered or gameplay testing'})
(O/'import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');u.log('M1911_HERO_IMPORT_COMPLETE')
