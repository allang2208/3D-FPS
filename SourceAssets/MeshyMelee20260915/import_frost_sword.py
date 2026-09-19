"""Import the new mesh/PBR assets using the existing sword skeleton and actions."""
from pathlib import Path
import json
import unreal as u

P=Path(__file__).parent
D='/Game/Weapons/FrostCrystalSword20260915'
DONOR='/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny'
A=u.AssetToolsHelpers.get_asset_tools()
receipt=[]
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')

def task(file,name,options=None):
    t=u.AssetImportTask();t.filename=str(file)
    t.destination_path=D;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=True
    if options:t.options=options
    A.import_asset_tasks([t])
    asset=u.load_asset(D+'/'+name)
    if not t.imported_object_paths or not asset:raise RuntimeError('Import failed: '+str(file))
    receipt.append({'source':str(file),'asset':asset.get_path_name()})
    return asset

source=next((P/'Original').rglob('*.fbx'))
textures={}
for suffix,name in [('', 'BaseColor'),('_normal','Normal'),('_metallic','Metallic'),('_roughness','Roughness')]:
    tex=task(source.with_name(source.stem+suffix+'.png'),'T_FrostCrystalSword_'+name)
    tex.set_editor_property('srgb',name=='BaseColor')
    if name=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',True)
    elif name in ['Metallic','Roughness']:
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    u.EditorAssetLibrary.save_loaded_asset(tex);textures[name]=tex

mat=u.load_asset(D+'/M_FrostCrystalSword') or A.create_asset('M_FrostCrystalSword',D,u.Material,u.MaterialFactoryNew())
mat.set_editor_property('used_with_skeletal_mesh',True)
E=u.MaterialEditingLibrary
E.delete_all_material_expressions(mat)
for i,(name,prop) in enumerate([('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Normal',u.MaterialProperty.MP_NORMAL),('Metallic',u.MaterialProperty.MP_METALLIC),('Roughness',u.MaterialProperty.MP_ROUGHNESS)]):
    node=E.create_material_expression(mat,u.MaterialExpressionTextureSample,-500,i*200)
    node.texture=textures[name]
    node.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if name=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if name in ['Metallic','Roughness'] else u.MaterialSamplerType.SAMPLERTYPE_COLOR
    E.connect_material_property(node,'R' if name in ['Metallic','Roughness'] else 'RGB',prop)
E.recompile_material(mat)
u.EditorAssetLibrary.save_loaded_asset(mat)

opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
opt.static_mesh_import_data.combine_meshes=True
opt.static_mesh_import_data.auto_generate_collision=True
mesh=task(P/'Export/SM_FrostCrystalSword.fbx','SM_FrostCrystalSword',opt)
mesh.set_material(0,mat)
u.EditorAssetLibrary.save_loaded_asset(mesh)

donor=u.load_asset(DONOR)
if not donor:raise RuntimeError('Existing two-handed sword mesh is required: '+DONOR)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False
opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
opt.skeleton=donor.skeleton
mesh=task(P/'Export/SK_FrostCrystalSword_Manny.fbx','SK_FrostCrystalSword_Manny',opt)
bindings={str(slot.material_slot_name):slot.material_interface for slot in donor.get_editor_property('materials')}
bindings['M_FrostCrystalSword']=mat
slots=mesh.get_editor_property('materials')
for i,slot in enumerate(slots):
    name=str(slot.material_slot_name)
    if name not in bindings:raise RuntimeError('Missing material source: '+name)
    slot.material_interface=bindings[name];slots[i]=slot
mesh.set_editor_property('materials',slots)
mesh.set_editor_property('positive_bounds_extension',u.Vector(120,120,120))
mesh.set_editor_property('negative_bounds_extension',u.Vector(120,120,120))
u.EditorAssetLibrary.save_loaded_asset(mesh)
(P/'import_receipt.json').write_text(json.dumps({
    'assets':receipt,'material':mat.get_path_name(),
    'shared_skeleton':donor.skeleton.get_path_name(),
    'shared_animation_folder':'/Game/Weapons/AzureRunesword20260913',
    'testing':'No preview, rendering, gameplay tests or acceptance checks run.'
},indent=2),encoding='utf-8')
u.log('FROST_CRYSTAL_SWORD_IMPORT_COMPLETE')
