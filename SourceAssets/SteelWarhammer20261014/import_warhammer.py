"""Import the selected warhammer and save assets through the project batch bridge."""
import json,sys
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1];D='/Game/Weapons/SteelWarhammer20261014'
sys.path.insert(0,str(P))
from warhammer_surface import build_surface
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project for warhammer import')
is_commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not is_commandlet:
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before importing warhammer assets')
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary
receipt={'assets':[],'complete':False,'tested':False,'animation_policy':'Direct shared pickaxe sequences'}
def save(obj):
    if not obj or not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed: '+str(obj))
    receipt['assets'].append(obj.get_path_name());(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');return obj
def imp(file,name,folder,options=None):
    obj=u.load_asset(folder+'/'+name)
    if obj:return obj
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=folder;t.destination_name=name;t.automated=True;t.save=False;t.replace_existing=False
    if options:t.options=options
    A.import_asset_tasks([t]);obj=u.load_asset(folder+'/'+name)
    if not obj:raise RuntimeError('Import failed: '+str(file))
    return obj
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(D+'/'):raise RuntimeError('Unsaved warhammer package: '+package.get_name())
tex={}
for key in ('BaseColor','MetallicRoughness','Normal'):
    t=imp(P/'Textures'/(key+'.jpg'),'T_SteelWarhammer_'+key,D+'/Textures')
    t.set_editor_property('srgb',key=='BaseColor');t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_MASKS if key=='MetallicRoughness' else u.TextureCompressionSettings.TC_DEFAULT)
    if key=='Normal':t.set_editor_property('flip_green_channel',True)
    tex[key]=save(t)
mat=u.load_asset(D+'/Materials/M_SteelWarhammerSurface')
if not mat:
    mat=A.create_asset('M_SteelWarhammerSurface',D+'/Materials',u.Material,u.MaterialFactoryNew())
build_surface(mat,tex)
save(mat)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=True;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
world=imp(P/'Export/SM_SteelWarhammer.fbx','SM_SteelWarhammer',D,opt);world.set_material(0,mat);save(world)
donor=u.load_asset('/Game/Items/ProductionTools/RusticPickaxe20260919/SK_RusticPickaxe')
bare=u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/Pickaxe/SK_Pickaxe_BareArmsV7')
if not donor or not bare:raise RuntimeError('Current pickaxe skeleton or native bare arms unavailable')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_mesh=True;opt.import_as_skeletal=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=donor.get_editor_property('skeleton')
opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
mesh=imp(P/'Export/SK_SteelWarhammer_BareArmsV7.fbx','SK_SteelWarhammer_BareArmsV7',D,opt)
bindings={str(m.material_slot_name):m.material_interface for m in bare.get_editor_property('materials')};bindings['M_SteelWarhammerSurface']=mat
for author,native in [('Skin_UpperArm','BareUpperArms'),('Skin_Forearm','BareLowerArms'),('Skin_Hand','BareHandsOriginalGrip')]:
    bindings[author]=bindings[native]
slots=mesh.get_editor_property('materials');skin_indices=[]
for i,slot in enumerate(slots):
    key=str(slot.material_slot_name)
    if key not in bindings:raise RuntimeError('Unbound warhammer material slot: '+key)
    slot.material_interface=bindings[key]
    slots[i]=slot  # Unreal struct-array iteration returns a value copy.
    if key!='M_SteelWarhammerSurface':skin_indices.append(i)
mesh.set_editor_property('materials',slots);save(mesh)
# Reuse native bare hands, shirts and gloves on the same skeleton and hand frames.
path=ROOT/'Content/ColdSteelData/modular_outfits.json';catalog=json.loads(path.read_text(encoding='utf-8-sig'))
profiles=catalog['profiles'] if 'profiles' in catalog else catalog['meshes']
donor_path=donor.get_path_name();profile=dict(profiles[donor_path]);profile['hide_source_materials']=skin_indices;profile['native_bare_arms']=True
profiles[mesh.get_path_name()]=profile
backup=P/'Before/modular_outfits.json'
if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(path.read_bytes())
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
icon_path=P/'Export/ue_steel_warhammer.png'
if icon_path.exists():
    icon=imp(icon_path,'ue_steel_warhammer','/Game/ColdSteelData/Icons');icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(icon)
receipt.update(complete=True,skin_material_indices=skin_indices,skeleton=mesh.get_editor_property('skeleton').get_path_name())
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt))
