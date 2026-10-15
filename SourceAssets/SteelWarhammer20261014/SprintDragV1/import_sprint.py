"""Save the independent warhammer carry, handoff, and native bare mesh revision."""
import unreal as u,json,re,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/SteelWarhammer20261014/SprintDragV1'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Stop PIE before importing')
A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;receipt={'saved':[],'complete':False,'runtime_tested':False}
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed: '+obj.get_path_name())
    receipt['saved'].append(obj.get_path_name());(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));return obj
def imp(path,name,options):
    obj=u.load_asset(D+'/'+name)
    if obj:return obj
    t=u.AssetImportTask();t.filename=str(path);t.destination_path=D;t.destination_name=name;t.automated=True;t.save=False;t.replace_existing=False;t.options=options
    A.import_asset_tasks([t]);obj=u.load_asset(D+'/'+name)
    if not obj:raise RuntimeError('Import failed: '+name)
    return obj
donor=u.load_asset('/Game/Items/ProductionTools/RusticPickaxe20260919/SK_RusticPickaxe');skeleton=donor.get_editor_property('skeleton')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_mesh=True;opt.import_as_skeletal=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;opt.skeletal_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
mesh=imp(P/'RigSource/Export/SK_SteelWarhammer_BareArmsV7.fbx','SK_Warhammer_BareArmsSprintV1',opt)
bare=u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/Pickaxe/SK_Pickaxe_BareArmsV7')
native={str(m.material_slot_name):m.material_interface for m in bare.materials}
materials={'M_SteelWarhammerSurface':u.load_asset('/Game/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface'),'Skin_UpperArm':native['BareUpperArms'],'Skin_Forearm':native['BareLowerArms'],'Skin_Hand':native['BareHandsOriginalGrip']}
slots=mesh.get_editor_property('materials');skin=[]
for i,slot in enumerate(slots):
    key=str(slot.material_slot_name);slot.material_interface=materials[key]
    slots[i]=slot  # Persist the edited struct back into the Unreal array.
    if key!='M_SteelWarhammerSurface':skin.append(i)
mesh.set_editor_property('materials',slots);save(mesh)
for name in ('A_Warhammer_SprintCarry','A_Warhammer_SprintAttack'):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',150)
    anim=imp(P/'Export'/(name+'.fbx'),name,opt)
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    if compression:anim.set_editor_property('bone_compression_settings',compression)
    save(anim)
# Keep existing inventory instances and equip/save contracts; publish only after assets save.
items=R/'Content/ColdSteelData/items.json';text=items.read_text(encoding='utf-8-sig');match=re.search(r'"ue_steel_warhammer"\s*:\s*\{[^}]*\}',text)
if not match:raise RuntimeError('Warhammer item unavailable')
old=match.group();new=old
for key in ('tool_viewmodel','viewmodel_mesh'):
    new=re.sub(r'("'+key+r'"\s*:\s*")[^"]*',lambda m:m.group(1)+mesh.get_path_name(),new)
before=P/'Before';before.mkdir(exist_ok=True)
if not (before/'items.json').exists():shutil.copy2(items,before/'items.json')
items.write_text(text[:match.start()]+new+text[match.end():],encoding='utf-8')
profile_path=R/'Content/ColdSteelData/modular_outfits.json';catalog=json.loads(profile_path.read_text(encoding='utf-8-sig'))
profile=dict(catalog['profiles'][donor.get_path_name()]);profile['hide_source_materials']=skin;profile['native_bare_arms']=True
catalog['profiles'][mesh.get_path_name()]=profile
if not (before/'modular_outfits.json').exists():shutil.copy2(profile_path,before/'modular_outfits.json')
profile_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt.update(complete=True,mesh=mesh.get_path_name(),skin_material_indices=skin)
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
