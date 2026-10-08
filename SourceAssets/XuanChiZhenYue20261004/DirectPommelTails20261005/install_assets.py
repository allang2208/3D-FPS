"""Save direct tassel attachments and the missing shared rune category icon."""
import copy,json,shutil,hashlib
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/XuanChiZhenYue20261004/DirectPommelTails20261005'
BASE='/Game/Weapons/XuanChiZhenYue20261004'
REV='XuanChiDirectPommelTails20261005';FINISH='xuanchi_direct_tail_v2'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Exit PIE before saving the pommel tail assemblies; no assets changed')
spec=json.loads((P/'exports.json').read_text(encoding='utf-8'))
receipt={'complete':False,'assets':[],'catalogs':[],'game_tested':False,'native_build_required':False}

def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def loaded(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Required saved asset is missing: '+path)
    return obj
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):
        raise RuntimeError('Save failed: '+obj.get_path_name())
    receipt['assets'].append(obj.get_path_name());record()
def asset(name):return D+'/Meshes/'+name+'.'+name

materials={
    'M_XuanChi_WeightedTassel':loaded(BASE+'/SurfaceV2/Materials/M_XuanChi_Tassel_V2'),
    'M_XuanChi_ExistingMount':loaded(BASE+'/SurfaceV2/Materials/M_XuanChi_Mount_V2'),
    'M_XuanChi_TerminalCopper':loaded(BASE+'/CommonGrips20261005/Materials/M_XuanChi_GripCopper'),
}
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
world=None
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')

def import_mesh(name,deforming=False):
    path=D+'/Meshes/'+name;obj=u.load_asset(path)
    if obj and E.get_metadata_tag(obj,'XuanChiTailRevision')!=REV:
        raise RuntimeError('Preserved unowned asset: '+path)
    if not obj:
        cfg=u.FbxImportUI();cfg.automated_import_should_detect_type=False
        cfg.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;cfg.import_as_skeletal=False
        cfg.import_mesh=True;cfg.import_materials=False;cfg.import_textures=False;cfg.import_animations=False
        data=cfg.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
        data.generate_lightmap_u_vs=False;data.build_nanite=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
        task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'))
        task.destination_path=D+'/Meshes';task.destination_name=name;task.automated=True
        task.replace_existing=False;task.save=False;task.options=cfg
        A.import_asset_tasks([task]);obj=u.load_asset(path)
        if not obj or not task.imported_object_paths:raise RuntimeError('Import failed: '+path)
        E.set_metadata_tag(obj,'XuanChiTailRevision',REV)
    slot_records=[]
    for i,slot in enumerate(obj.static_materials):
        slot_name=str(slot.material_slot_name)
        key=next((key for key in materials if slot_name.startswith(key)),None)
        if not key:raise RuntimeError('Unmapped tail material slot: '+slot_name)
        obj.set_material(i,materials[key]);slot_records.append({'slot':slot_name,'material':materials[key].get_path_name()})
    build=sm.get_lod_build_settings(obj,0)
    build.recompute_normals=False;build.recompute_tangents=True;build.use_mikk_t_space=True
    build.use_full_precision_u_vs=True;sm.set_lod_build_settings(obj,0,build)
    E.set_metadata_tag(obj,'NativeTailWeightsPreserved','true' if deforming else 'not_applicable')
    save(obj);receipt.setdefault('mesh_materials',{})[name]=slot_records;record()
    return slot_records

tail_slots=import_mesh(spec['tail_mesh'],True)
adapter_slots={row['option']:import_mesh(row['adapter_mesh']) for row in spec['options']}

def merge_file(path,merge):
    original=path.read_bytes();value=json.loads(original.decode('utf-8-sig'));merge(value)
    backup=P/'Before'/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(original)
    if path.read_bytes()!=original:raise RuntimeError('Catalog changed during write: '+str(path))
    temporary=path.with_suffix('.xuanchi-tails.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path);receipt['catalogs'].append(str(path));record()

catalog_path=ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json'
catalog=json.loads(catalog_path.read_text(encoding='utf-8-sig'))
base_finish=catalog.get('pommel_tail_base_finish',catalog['pommel_profile']['finish'])
receipt['preserved_bone_mount']=copy.deepcopy(catalog['bone_mount'])
receipt['body_finish']=base_finish

def library_merge(value):
    theme={}
    for row in spec['options']:
        key=row['option']
        # Reuse all body/gem materials from the accepted shared finish.
        entry=copy.deepcopy(value['finishes'].get(base_finish,{}).get(key,{}))
        entry['adapter']={
            'mesh':asset(row['adapter_mesh']),'location_cm':row['adapter_location_cm'],
            'rotation_deg':[0,0,0],'scale':[1,1,1],
            'interface':'xuanchi_'+row['interface']+'_direct_tassel',
            'materials':{s['slot']:s['material'] for s in adapter_slots[key]},
        }
        entry['tassel']={
            'mesh':asset(spec['tail_mesh']),'location_cm':row['tassel_location_cm'],
            'rotation_deg':[0,0,0],'scale':[1,1,1],
            'guides_cm':row['guides_cm'],'collision_capsules_cm':row['collision_capsules_cm'],
            'materials':{s['slot']:s['material'] for s in tail_slots},
            'appearance':'末端直连赤绳玉坠与柔性剑穗',
        }
        entry['appearance']=value['options'][key]['appearance']+' · 直连玉坠'
        theme[key]=entry
    value['finishes'][FINISH]=theme

def catalog_merge(value):
    value['pommel_profile']['finish']=FINISH
    value['pommel_tail_base_finish']=base_finish
    value['pommel_tail_revision']=REV

# Publish only after every new mesh and its material bindings are saved.
merge_file(ROOT/'Content/ColdSteelData/shared-sword-pommels.json',library_merge)
merge_file(catalog_path,catalog_merge)

# The category parser already falls back to category_<slot>.png. The original
# XuanChi deployment simply omitted blade_2; promote the approved rune artwork
# to its one shared key, with no new per-weapon copy or UI code branch.
icons=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
source_icon=icons/'ue_tang_dao_category_blade_2.png'
target_icon=icons/'category_blade_2.png'
if not target_icon.exists():shutil.copy2(source_icon,target_icon)
task=u.AssetImportTask();task.filename=str(target_icon)
task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913'
task.destination_name='category_blade_2';task.automated=True
task.replace_existing=True;task.replace_existing_settings=False;task.save=False
A.import_asset_tasks([task])
texture=loaded(task.destination_path+'/category_blade_2')
texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',True)
save(texture)
def icon_manifest(value):
    job={'source':str(source_icon),'file':str(target_icon),'asset':task.destination_path+'/category_blade_2','slot':'blade_2'}
    previous=next((row for row in value if Path(row['file']).stem=='category_blade_2'),None)
    if previous is None:value.append(job)
    else:previous.update(job)
merge_file(P.parent/'ModelV1/Icons/deployments.json',icon_manifest)
receipt['rune_category_icon']={'source':str(source_icon),'shared':str(target_icon),
    'asset':texture.get_path_name(),'sha256':hashlib.sha256(target_icon.read_bytes()).hexdigest()}
receipt.update(complete=True,options=[row['option'] for row in spec['options']],
    modified_counterweight_rings_removed=True,retained_factory_ring=True,shared_bodies_unchanged=True,
    common_grip_pommel_offset_reused=True,physics='Existing SwordTasselMeshComponent and original eight-guide weights')
record()
print('XUANCHI_DIRECT_POMMEL_TAILS_SAVED '+json.dumps({'assets':len(receipt['assets']),
    'options':receipt['options'],'complete':True,'game_tested':False}),flush=True)
