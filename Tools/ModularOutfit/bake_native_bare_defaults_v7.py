"""Bake bare arms into existing viewmodels; retain original gloves as equipment.

Run through Run-Authoring.ps1 after closing the FPSGAME editor. This preserves
native weapon slots, bones, sockets, animation bindings and weapon geometry.
"""
import hashlib,json,shutil
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7'
DEST='/Game/Characters/ModularOutfit20260924/BarePalmV7'
RECEIPTS=ROOT/'NativeDefaults';RECEIPTS.mkdir(parents=True,exist_ok=True)
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
M=u.GeometryScript_Materials;Ed=u.GeometryScript_MeshEdits;L=u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
config_path=PROJECT/'Content/ColdSteelData/modular_outfits.json'
config=json.loads(config_path.read_text(encoding='utf-8-sig'))
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Finish play before native mesh authoring')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def dynamic(asset):
    dm,out=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if out!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+asset.get_path_name())
    return dm
def write(dm,asset,mats,names):
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=names,
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,out=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
    if out!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot author '+asset.get_path_name())
def precise(asset):
    for i in range(S.get_lod_count(asset)):
        build=S.get_lod_build_settings(asset,i);build.set_editor_property('use_full_precision_u_vs',True)
        S.set_lod_build_settings(asset,i,build)

# A single skin material selects hand vs arm from the authored vertex mask.
# Native arm material indices stay identical, including world-copy hiding rules.
parent_path=DEST+'/Materials/M_BareNative_Default'
if E.does_asset_exist(parent_path):parent=load(parent_path)
else:
    parent=A.duplicate_asset('M_BareNative_Default',DEST+'/Materials',load(DEST+'/Materials/M_BareFamily_Hands'))
    custom=L.get_material_property_input_node(parent,u.MaterialProperty.MP_NORMAL)
    colours=L.create_material_expression(parent,u.MaterialExpressionVertexColor)
    if not L.connect_material_expressions(colours,'R',custom,'ForearmMode'):raise RuntimeError('Cannot connect arm region mask')
    custom.set_editor_property('code',custom.get_editor_property('code').replace(
        'AnatomicalNormal.xy*lerp(1,.58,palmar*(1-nail))',
        'AnatomicalNormal.xy*(1-ForearmMode)*lerp(1,.58,palmar*(1-nail))'))
    L.set_material_usage(parent,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    errors=L.recompile_material(parent)
    if errors:raise RuntimeError('Cannot compile default skin: '+str(errors))
    save(parent)
instance_path=DEST+'/Materials/MI_BareNative_Default'
skin=load(instance_path) if E.does_asset_exist(instance_path) else A.create_asset('MI_BareNative_Default',DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
L.set_material_instance_parent(skin,parent);L.update_material_instance(skin);save(skin)
if not (RECEIPTS/'modular_outfits.before.json').exists():shutil.copy2(config_path,RECEIPTS/'modular_outfits.before.json')

for path,profile in config['profiles'].items():
    key=profile['rig_profile']
    if key=='Body':continue
    bare_receipt=json.loads((ROOT/'Saved'/f'{key}.json').read_text())
    receipt_path=RECEIPTS/f'{key}.json'
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text())
        if receipt['authored_sha256']==bare_receipt['authored_sha256']:
            profile.update(receipt['profile_fields']);continue
    print('NATIVE_BARE_BEGIN',key,flush=True)
    source=load(path);arm_ids=profile['hide_source_materials']
    if len(arm_ids)!=2:raise RuntimeError('Author a slot mapping before modifying '+key+': '+str(arm_ids))
    # Keep both an engine-readable duplicate and an exact pre-edit disk package.
    backup_name='SK_'+key+'_GlovedSource';backup_path=DEST+'/OriginalSources/'+backup_name
    source_file=PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    backup_file=RECEIPTS/'Packages'/f'{key}.uasset';backup_file.parent.mkdir(parents=True,exist_ok=True)
    if not backup_file.exists():shutil.copy2(source_file,backup_file)
    if E.does_asset_exist(backup_path):original=load(backup_path)
    else:
        original=A.duplicate_asset(backup_name,DEST+'/OriginalSources',source);save(original)
    slots=[s.copy() for s in original.materials]
    native_slots=[s.copy() for s in source.materials]
    original_dm=dynamic(source)

    # Extract original arms on their exact native skeleton for the existing item.
    restore_name='SK_'+key+'_OriginalGlovedArms';restore_path=DEST+'/OriginalGloves/'+restore_name
    if E.does_asset_exist(restore_path):restore=load(restore_path)
    else:
        restore_dm=dynamic(original)
        for material in range(len(slots)):
            if material not in arm_ids:M.delete_triangles_by_material_id(restore_dm,material,True)
        for i,material in enumerate(arm_ids):M.remap_material_i_ds(restore_dm,material,1000+i)
        for i in range(len(arm_ids)):M.remap_material_i_ds(restore_dm,1000+i,i)
        restore=A.duplicate_asset(restore_name,DEST+'/OriginalGloves',original)
        write(restore_dm,restore,[slots[i].material_interface for i in arm_ids],[slots[i].material_slot_name for i in arm_ids])
        restore.set_editor_property('physics_asset',None)
        if not u.FPSModularOutfitComponent.configure_outfit_lods(restore):raise RuntimeError('Cannot configure original glove LODs '+key)
        if not S.regenerate_lod(restore,3,True,False):raise RuntimeError('Cannot build original glove LODs '+key)
        save(restore)

    # Retain the weapon triangles and all mechanical bindings verbatim in LOD0.
    for material in arm_ids:M.delete_triangles_by_material_id(original_dm,material,True)
    bare=load(bare_receipt['mesh']);bare_dm=dynamic(bare)
    for i in range(3):M.remap_material_i_ds(bare_dm,i,1000+i)
    for i,material in enumerate((arm_ids[0],arm_ids[1],arm_ids[1])):M.remap_material_i_ds(bare_dm,1000+i,material)
    Ed.append_mesh(original_dm,bare_dm,u.Transform(),True)
    mats=[s.material_interface for s in native_slots]
    for material in arm_ids:mats[material]=skin
    lod_count=S.get_lod_count(source)
    write(original_dm,source,mats,[s.material_slot_name for s in native_slots])
    precise(source)
    if lod_count>1 and not S.regenerate_lod(source,lod_count,True,False):raise RuntimeError('Cannot rebuild native LODs '+key)
    E.set_metadata_tag(source,'BareArmsDefault','V7; native geometry, no runtime replacement')
    E.set_metadata_tag(source,'OriginalGlovedSource',original.get_path_name());save(source)
    fields={'native_bare_arms':True,'native_bare_skin':bare.get_path_name(),'base':bare.get_path_name(),
        'bare_arms_candidate':bare.get_path_name(),'original_gloved_arms':restore.get_path_name(),
        'original_gloved_source':original.get_path_name(),'shirt_covers':[0,1],'glove_covers':[2]}
    profile.update(fields)
    receipt={'profile':key,'source':path,'original_source':original.get_path_name(),
        'disk_backup':str(backup_file),'authored_sha256':bare_receipt['authored_sha256'],
        'profile_fields':fields,'runtime_tested':False}
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    # Each asset/config pair is committed together, so interruption is resumable.
    latest=json.loads(config_path.read_text(encoding='utf-8-sig'))
    latest['profiles'][path].update(fields)
    config_path.write_text(json.dumps(latest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('NATIVE_BARE_SAVED',key,flush=True)
latest=json.loads(config_path.read_text(encoding='utf-8-sig'))
for path,profile in config['profiles'].items():
    if profile['rig_profile']=='Body':continue
    receipt=json.loads((RECEIPTS/(profile['rig_profile']+'.json')).read_text())
    latest['profiles'][path].update(receipt['profile_fields'])
config_path.write_text(json.dumps(latest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('NATIVE_BARE_DEFAULTS_COMPLETE',sum(p['rig_profile']!='Body' for p in config['profiles'].values()),flush=True)
