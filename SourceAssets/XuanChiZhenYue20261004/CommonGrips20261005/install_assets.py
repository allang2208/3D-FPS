"""Save five fitted grips, retained PBR, shared icons and scoped catalog entries."""
import copy,hashlib,json,shutil
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/XuanChiZhenYue20261004/CommonGrips20261005'
SHARED='/Game/Weapons/SharedSwordGrips20260927'
ICONS=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
ICON_UE='/Game/ColdSteelData/AttachmentIcons20260913'
L,E=u.MaterialEditingLibrary,u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools();REV='XuanChiCommonGrips20261005'
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Exit PIE before importing the grip modules; no assets changed')
spec=json.loads((P/'exports.json').read_text(encoding='utf-8'))
receipt={'complete':False,'assets':[],'icons':[],'retired_overrides':[],
    'game_tested':False,'native_build_required':False}

def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Asset save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());record()
def connect(a,pin,b,target):
    if not L.connect_material_expressions(a,pin,b,target):raise RuntimeError('Grip material connection failed: '+target)
def loaded(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Required production asset is missing: '+path)
    return asset
def srgb(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4

catalog=json.loads((ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json').read_text(encoding='utf-8-sig'))
factory=loaded(catalog['slots']['grip']['factory']['mesh'])
stock_material=factory.get_material(0)
leather=loaded(SHARED+'/Materials/M_SharedGrip_Leather')
textile=loaded(SHARED+'/Materials/M_SharedGrip_Textile')
steel=loaded(SHARED+'/Materials/M_SharedGrip_Steel')
long_profile=loaded('/Game/Weapons/AnimationProfiles20261001/Melee/DA_Sword_LongGrip')
receipt['shared_long_grip_profile']=long_profile.get_path_name()
receipt['preserved_bone_mount']=copy.deepcopy(catalog['bone_mount'])

material_path=D+'/Materials/M_XuanChi_GripCopper'
copper=u.load_asset(material_path)
if not copper:
    copper=E.duplicate_asset(steel.get_path_name(),material_path)
    if not copper:raise RuntimeError('Could not create the host copper material')
    E.set_metadata_tag(copper,'XuanChiGripRevision',REV)
elif E.get_metadata_tag(copper,'XuanChiGripRevision')!=REV:
    raise RuntimeError('Preserved unowned copper material: '+material_path)
if E.get_metadata_tag(copper,'XuanChiCopperGraphComplete')!='true':
    slab=L.get_material_property_input_node(copper,u.MaterialProperty.MP_FRONT_MATERIAL)
    sample=L.get_inputs_for_material_expression(copper,slab)[0]
    gray=L.create_material_expression(copper,u.MaterialExpressionDesaturation)
    amount=L.create_material_expression(copper,u.MaterialExpressionConstant);amount.set_editor_property('r',1.)
    tint=L.create_material_expression(copper,u.MaterialExpressionVectorParameter)
    tint.set_editor_property('parameter_name','CopperTint')
    tint.set_editor_property('default_value',u.LinearColor(*(srgb(c/255)*2.5 for c in [222,157,109]),1.))
    multiply=L.create_material_expression(copper,u.MaterialExpressionMultiply)
    connect(sample,'',gray,'');connect(amount,'',gray,'Fraction')
    connect(gray,'',multiply,'A');connect(tint,'RGB',multiply,'B')
    connect(multiply,'',slab,'BaseColor')
    if not L.connect_material_property(multiply,'',u.MaterialProperty.MP_BASE_COLOR):raise RuntimeError('Copper base output failed')
    metallic=L.create_material_expression(copper,u.MaterialExpressionConstant);metallic.set_editor_property('r',.97)
    connect(metallic,'',slab,'Metallic');L.connect_material_property(metallic,'',u.MaterialProperty.MP_METALLIC)
    E.set_metadata_tag(copper,'XuanChiCopperGraphComplete','true');L.layout_material_expressions(copper)
errors=list(L.recompile_material(copper) or [])
if errors:raise RuntimeError('Copper material compile failed: '+str(errors))
save(copper)
temporal=u.load_asset(material_path+'_Whirlwind')
if not temporal:
    temporal=E.duplicate_asset(copper.get_path_name(),material_path+'_Whirlwind')
    response=L.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
    one=L.create_material_expression(temporal,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
    connect(one,'',response,'')
    E.set_metadata_tag(temporal,'XuanChiGripRevision',REV)
errors=list(L.recompile_material(temporal) or [])
if errors:raise RuntimeError('Copper temporal material compile failed: '+str(errors))
save(temporal)

materials={'M_XuanChi_Hilt_V2':stock_material,'M_SharedGrip_Leather':leather,
    'M_XuanChi_GripCopper':copper,'M_SharedGrip_Textile':textile}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for row in spec['options']:
    path=D+'/Meshes/'+row['mesh'];mesh=u.load_asset(path)
    if not mesh:
        cfg=u.FbxImportUI();cfg.automated_import_should_detect_type=False
        cfg.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        cfg.import_as_skeletal=False;cfg.import_mesh=True
        cfg.import_materials=False;cfg.import_textures=False;cfg.import_animations=False
        data=cfg.static_mesh_import_data
        data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
        data.build_nanite=factory.get_editor_property('nanite_settings').enabled
        task=u.AssetImportTask();task.filename=str(P/'Export'/(row['mesh']+'.fbx'))
        task.destination_path=D+'/Meshes';task.destination_name=row['mesh']
        task.automated=True;task.replace_existing=False;task.save=False;task.options=cfg
        A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh or not task.imported_object_paths:raise RuntimeError('Grip import failed: '+path)
    for i,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name)
        if key not in materials:raise RuntimeError('Unmapped grip material slot: '+key)
        mesh.set_material(i,materials[key])
    build=sm.get_lod_build_settings(mesh,0)
    build.recompute_normals=False;build.recompute_tangents=True;build.use_mikk_t_space=True;build.use_full_precision_u_vs=True
    sm.set_lod_build_settings(mesh,0,build)
    E.set_metadata_tag(mesh,'XuanChiGripRevision',REV);save(mesh)

# Promote existing framed representative artwork once for these common IDs.
before=P/'Before/Icons';before.mkdir(parents=True,exist_ok=True)
retired=ROOT/'trash/xuanchi-common-grip-icons-20261005';retired.mkdir(parents=True,exist_ok=True)
for row in spec['options']:
    option=row['option'];key='grip_'+option
    donor='ue_frost_crystal_sword' if option in ['iron_spine_power_grip','lockweave_guard_grip'] else 'ue_tang_dao'
    source=ICONS/(donor+'_'+key+'.png');target=ICONS/(key+'.png')
    for old in [target,target.with_suffix('.uasset')]:
        if old.exists() and not (before/old.name).exists():shutil.copy2(old,before/old.name)
    shutil.copy2(source,target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_path=ICON_UE;task.destination_name=key
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=False;task.save=False
    A.import_asset_tasks([task]);tex=loaded(ICON_UE+'/'+key)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True);save(tex)
    receipt['icons'].append({'source':str(source),'shared':str(target),'asset':tex.get_path_name(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    old=ICONS/('ue_xuanchi_zhenyue_'+key+'.png')
    if old.exists():
        destination=retired/old.name;digest=hashlib.sha256(old.read_bytes()).hexdigest()
        if not destination.exists():shutil.copy2(old,destination)
        if hashlib.sha256(destination.read_bytes()).hexdigest()!=digest:raise RuntimeError('Retirement destination differs: '+str(destination))
        old.unlink();receipt['retired_overrides'].append({'file':str(old),'retained_at':str(destination),'sha256':digest,'replacement':str(target)})
    record()

def update_json(path,merge):
    original=path.read_bytes();value=json.loads(original.decode('utf-8-sig'));merge(value)
    backup=P/'Before'/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(original)
    if path.read_bytes()!=original:raise RuntimeError('Catalog changed during merge; saved assets retained: '+str(path))
    temporary=path.with_suffix(path.suffix+'.xuanchi-grips.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(path)

def modules(value):
    for row in spec['options']:
        entry=copy.deepcopy(value['slots']['grip']['factory'])
        entry.update(mesh=D+'/Meshes/'+row['mesh']+'.'+row['mesh'],pommel_offset_cm=row['pommel_offset_cm'])
        entry.pop('materials',None)
        entry['appearance']={'shock_wrap':'交错缓冲缠带 · 原形铜套接口',
            'swift_grip':'收束握腰 · 浅导向槽与铜色细脊',
            'long_twohand':'加长双手握区 · 柄尾与剑穗联动',
            'iron_spine_power_grip':'贴平铜色金属脊 · 三段皮革握区',
            'lockweave_guard_grip':'交错锁纹织带 · 原形铜套接口'}[row['option']]
        if row['animation_folder']:entry['animation_folder']=row['animation_folder']
        value['slots']['grip'][row['option']]=entry
    value['grip_surface_revision']=REV
def options(value):
    column=next(c for c in value['columns'] if c['key']=='grip')
    for option in column['options']:
        if option['id'] in ['iron_spine_power_grip','lockweave_guard_grip']:
            if 'ue_xuanchi_zhenyue' not in option['weapons']:option['weapons'].append('ue_xuanchi_zhenyue')
def deployments(value):
    for row in spec['options']:
        key='grip_'+row['option'];target=str(ICONS/(key+'.png'))
        old=next((job for job in value if Path(job['file']).stem=='ue_xuanchi_zhenyue_'+key),None)
        job={'source':target,'file':target,'asset':ICON_UE+'/'+key,'slot':'grip'}
        if old is not None:old.update(job)
        elif not any(Path(j['file']).stem==key for j in value):value.append(job)
update_json(ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json',modules)
update_json(ROOT/'Content/ColdSteelData/melee-gunsmith.json',options)
update_json(ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json',lambda value:value.update({copper.get_path_name():temporal.get_path_name()}))
update_json(P.parent/'ModelV1/Icons/deployments.json',deployments)
(retired/'manifest.json').write_text(json.dumps(receipt['retired_overrides'],indent=2)+'\n',encoding='utf-8')
receipt.update(complete=True,catalogs_saved=True,options=[r['option'] for r in spec['options']],
    long_grip_extension_cm=3.5,stock_grip_material=stock_material.get_path_name())
record();print('XUANCHI_COMMON_GRIPS_SAVED '+json.dumps(receipt,ensure_ascii=False),flush=True)
