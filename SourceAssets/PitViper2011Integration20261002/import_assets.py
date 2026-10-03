"""Background production import into the new PitViper2011 asset family only."""
import copy,hashlib,json,re
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];DEST='/Game/Weapons/PitViper2011/Integrated20261002'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
receipt={'saved':[],'meshes':{},'animations':{},'materials':{},'audio':{},'runtime_tested':False,'rendered_for_acceptance':False}
attribution='Low Poly TTI JW4 Pit Viper 2011 by D_U; Sketchfab 2daaf7fe78604ee7941a4ad5fd4d0153; CC BY 4.0; modified: scale, rig, animation, native project arms, materials.'
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing production dependency: '+path)
    return a
def save(a):
    if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost()],False):raise RuntimeError('Save failed: '+a.get_path_name())
    if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
    record();return a
def create(name,folder,cls,factory):
    existing=u.load_asset(folder+'/'+name)
    if existing:return existing
    result=A.create_asset(name,folder,cls,factory)
    if not result:raise RuntimeError('Asset creation failed: '+folder+'/'+name)
    return result
def imported(file,folder,name,options=None):
    signature=hashlib.sha256(Path(file).read_bytes()).hexdigest();path=folder+'/'+name
    if E.does_asset_exist(path):
        a=load(path)
        if E.get_metadata_tag(a,'PitViperSourceSHA256')==signature and (not isinstance(a,u.SkeletalMesh) or a.skeleton):return a
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task]);a=load(path)
    if isinstance(a,u.SkeletalMesh) and a.skeleton:save(a.skeleton)
    E.set_metadata_tag(a,'PitViperSourceSHA256',signature);E.set_metadata_tag(a,'SourceAttribution',attribution);return save(a)

u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/Weapons/PitViper2011'],True)
recipe=json.loads((O/'finish_recipe.json').read_text(encoding='utf8'))['slots'];materials={}
for key,spec in recipe.items():
    name='MI_PitViper2011_'+key.replace('-','_');parent=load('/Game/Weapons/WeaponSurface/Presets/MI_WS_'+spec['preset'])
    mi=create(name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.clear_all_material_instance_parameters(mi);L.set_material_instance_parent(mi,parent)
    for param,value in {'SourceColorWeight':0.,'SourceRoughnessWeight':0.,'MaskUVChannel':0.,'Roughness':spec['roughness'],'Metallic':spec['metallic']}.items():L.set_material_instance_scalar_parameter_value(mi,param,value)
    L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*spec['color'],1))
    # Closed gun parts inherit the shared WS opaque-surface shader permutation.
    # Optical planes and the separate tritium material retain their own policy.
    overrides=mi.get_editor_property('base_property_overrides');overrides.set_editor_property('override_two_sided',False);mi.set_editor_property('base_property_overrides',overrides)
    L.update_material_instance(mi);E.set_metadata_tag(mi,'WeaponSurfacePreset',spec['preset']);E.set_metadata_tag(mi,'SourceAttribution',attribution);save(mi)
    materials[key.lower()]=mi;materials[key.lower().replace('-','_')]=mi
    receipt['materials'][key]={'asset':mi.get_path_name(),'parent':parent.get_path_name(),'recipe':spec}
tritium=create('M_PitViper2011_Tritium',DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(tritium)
for color,prop in [((.01,.75,.003,1),u.MaterialProperty.MP_BASE_COLOR),((.006,.65,.002,1),u.MaterialProperty.MP_EMISSIVE_COLOR)]:
    n=L.create_material_expression(tritium,u.MaterialExpressionConstant3Vector);n.constant=u.LinearColor(*color);L.connect_material_property(n,'',prop)
n=L.create_material_expression(tritium,u.MaterialExpressionConstant);n.r=.55;L.connect_material_property(n,'',u.MaterialProperty.MP_ROUGHNESS)
tritium.set_editor_property('two_sided',True);tritium.set_editor_property('used_with_skeletal_mesh',True);L.set_material_usage(tritium,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.recompile_material(tritium);save(tritium);materials['tritium']=tritium
materials['factorycompensator']=materials['h_190']
receipt['materials']['tritium']={'asset':tritium.get_path_name(),'purpose':'nonmetallic original green front sight'}
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
new_profiles={}
try:
    profiles=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['profiles']
    for key,relative,profile in [('single','Single','M1911'),('r','Dual/r','M1911_r'),('l','Dual/l','M1911_l')]:
        folder=O/relative;auth=json.loads((folder/'authoring.json').read_text())
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
        opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
        mesh=imported(folder/auth['mesh'],DEST+'/'+relative,Path(auth['mesh']).stem,opt)
        entry=copy.deepcopy(next(v for v in profiles.values() if v.get('rig_profile')==profile));bare=load(entry['base']);skin={name:slot.material_interface for name,slot in zip(('UpperArm','Forearm','Hand'),bare.materials)}
        slots=list(mesh.materials);arm_ids=[]
        for i,slot in enumerate(slots):
            name=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name))
            if 'Manny' in name:
                arm_ids.append(i);part=next((p for p in skin if p.lower() in name.lower()),'Hand');slot.material_interface=skin[part]
            else:
                material=name.lower().removeprefix('m_pitviper2011_');slot.material_interface=materials[material]
            slots[i]=slot
        mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
        for lod in range(S.get_lod_count(mesh)):
            settings=S.get_lod_build_settings(mesh,lod);settings.use_full_precision_u_vs=True;S.set_lod_build_settings(mesh,lod,settings)
        E.set_metadata_tag(mesh,'SourceAttribution',attribution);save(mesh);save(mesh.skeleton)
        entry.update(native_bare_arms=True,hide_source_materials=arm_ids);entry.pop('original_gloved_source',None);new_profiles[mesh.get_path_name()]=entry
        receipt['meshes'][key]={'asset':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}}
        for kind,clip in auth['clips'].items():
            file=folder/clip['file'];opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton;opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
            a=imported(file,DEST+'/'+relative+'/Animations',file.stem,opt);a.set_editor_property('bone_compression_settings',load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));save(a)
            receipt['animations'][key+'/'+kind]={'asset':a.get_path_name(),'duration':a.get_play_length()}
        record();print('PitViper2011_FAMILY_SAVED',key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
cues={'Fire':'/Game/Weapons/M1911/Integrated20260913/Audio/S_M1911_Fire',
 'MagOut':'/Game/Weapons/M4HK416Audio/S_HK416_MagOut','MagInsert':'/Game/Weapons/M4HK416Audio/S_HK416_MagInsert','MagSeat':'/Game/Weapons/M4HK416Audio/S_HK416_MagSeat',
 'Equip':'/Game/Weapons/M4AnimationAuditFinal/S_HK416_Equip','ChargePull':'/Game/Weapons/AKM/Audio/S_AKM_ChargePull',
 'ChargeRelease':'/Game/Weapons/M4AnimationAuditFinal/S_HK416_BoltRelease','DryClick':'/Game/Weapons/AKM/Audio/S_AKM_DryClick','CriticalHit':'/Game/Weapons/AKM/Audio/S_AKM_CriticalHit'}
for cue,source in cues.items():
    name='S_PitViper2011_'+cue;path=DEST+'/Audio/'+name;a=load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,DEST+'/Audio',load(source));save(a);receipt['audio'][cue]={'asset':a.get_path_name(),'source':source}
# The supplied firing one-shot is authoritative when its local recipe exists.
# Rebuilding this weapon must not restore the original M1911 donor sound.
fire_job=O.parent/'PitViper2011FireAudio20261002'
if (fire_job/'provenance.json').exists():
    script=fire_job/'import_audio.py'
    exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
    firing=json.loads((fire_job/'import_receipt.json').read_text(encoding='utf8'))
    recipe_audio=json.loads((fire_job/'provenance.json').read_text(encoding='utf8'))
    receipt['audio']['Fire'].update(source=firing['source'],source_kind='User-provided '+Path(recipe_audio['input_actual_path']).name+', locally processed',source_sha256=firing['source_sha256'],repair_receipt=str(fire_job/'import_receipt.json'))
file=P/'Content/ColdSteelData/Icons/ue_pit_viper2011.png';tex=imported(file,'/Game/ColdSteelData/Icons',file.stem)
tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;save(tex)
for file in sorted((P/'Content/ColdSteelData/AttachmentIcons20260913').glob('ue_pit_viper2011_*.png')):
    tex=imported(file,DEST+'/Icons',file.stem);tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;save(tex)
config=P/'Content/ColdSteelData/modular_outfits.json';text=config.read_text(encoding='utf-8-sig');start=text.index('{',text.index('"profiles"'));data,size=json.JSONDecoder().raw_decode(text[start:]);data.update(new_profiles)
if config.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Outfit catalog changed during publication')
config.write_text(text[:start]+json.dumps(data,ensure_ascii=False,indent=2)+text[start+size:],encoding='utf8')
script=O/'publish_catalog.py';exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
receipt.update(status='imported_and_saved',profiles=list(new_profiles),catalog_published=True);record()
finish=O.parent/'PitViper2011SurfaceRefine20261003/restore_saved_finish.py'
if finish.exists():
    import runpy
    runpy.run_path(str(finish),run_name='__main__')
print('PitViper2011_IMPORT_AND_SAVE_COMPLETE',flush=True)
