"""Save SI muzzle and native factory-compensator sections without animation import."""
import json,re,shutil,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/PitViper2011/SICompensator20261003'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring_receipt.json').read_text(encoding='utf8'))
families=json.loads((O/'Integration20261003/body_sections.json').read_text(encoding='utf8'))['families']
WET='/Game/Weapons/PistolGripSurface20260927/DA_PistolGripSurfaceWetMaterials'
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong production project')
receipt={'saved':[],'families':{},'runtime_tested':False,'acceptance_rendered':False}
def record():(O/'integration_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing dependency '+path)
    return a
def save(a):
    if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost()],False):raise RuntimeError('Save failed '+a.get_path_name())
    if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
    record();return a
def canon(name):return re.sub(r'[._]\d{3}$','',str(name)).lower().replace('-','_')
def imported(file,folder,name,options):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);return load(folder+'/'+name)
native={k:load(v['folder']+'/'+v['name']) for k,v in families.items()}
targets={D+'/SM_PitViper2011_SICompensator',WET}
targets.update(v['folder']+'/'+v['name'] for v in families.values())
targets.update(a.skeleton.get_outermost().get_path_name() for a in native.values())
targets.update(D+'/Materials/'+name for name in ('MI_SI_2011_CleanAnodized','MI_SI_RecessSteel','MI_SI_GrayLaserMark'))
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets&dirty:raise RuntimeError('Preserve unsaved SI target packages '+str(sorted(targets&dirty)))
for path in targets:
    file=P/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=O/'Integration20261003/Before/Content'/(path.removeprefix('/Game/')+'.uasset')
    if file.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,backup)
metal=load('/Game/Weapons/PitViper2011/Integrated20261002/Materials/MI_PitViper2011_h_190')
bindings={}
for label,name,source,params,color in [
 ('SI_2011_CleanAnodized','MI_SI_2011_CleanAnodized',metal,{},None),
 ('SI_RecessSteel','MI_SI_RecessSteel',load('/Game/Weapons/M4MuzzlesV1/MI_MuzzleRecess'),{},None),
 ('SI_GrayLaserMark','MI_SI_GrayLaserMark',load('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanPolymer'),
   {'SourceColorWeight':0.,'SourceRoughnessWeight':0.,'MaskUVChannel':1.,'Roughness':.68,'Metallic':0.},(.44,.46,.48))]:
    mi=u.load_asset(D+'/Materials/'+name) or A.duplicate_asset(name,D+'/Materials',source)
    if not mi:raise RuntimeError('Cannot create SI material '+name)
    for key,value in params.items():L.set_material_instance_scalar_parameter_value(mi,key,value)
    if color:L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*color,1))
    L.update_material_instance(mi);E.set_metadata_tag(mi,'SourceAttribution',auth['provenance']);save(mi);bindings[label]=mi
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.generate_lightmap_u_vs=False;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=imported(auth['fbx'],D,'SM_PitViper2011_SICompensator',opt)
    slots=list(mesh.static_materials)
    for i,s in enumerate(slots):
        label=re.sub(r'[._]\d{3}$','',str(s.material_slot_name));s.material_interface=bindings[label];slots[i]=s
    mesh.set_editor_property('static_materials',slots)
    for key,point in auth['sockets_blender_m'].items():
        name=key.removeprefix('SOCKET_');socket=mesh.find_socket(name)
        if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.socket_name=name;mesh.add_socket(socket)
        socket.relative_location=u.Vector(point[0]*100,-point[1]*100,point[2]*100)
    static=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    if static:
        settings=static.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;static.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'SourceAttribution',auth['provenance']);E.set_metadata_tag(mesh,'MountContract','rear mounting datum; replace FactoryCompensator section; WPN_Barrel parent')
    save(mesh);receipt['mesh']=mesh.get_path_name();receipt['materials']={k:v.get_path_name() for k,v in bindings.items()};record()
    arm_ids={};sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    for key,entry in families.items():
        existing=native[key];original={canon(s.material_slot_name):s.material_interface for s in existing.materials}
        skeleton=existing.skeleton
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
        opt.create_physics_asset=False;opt.skeleton=skeleton
        opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
        body=imported(entry['fbx'],entry['folder'],entry['name'],opt)
        slots=list(body.materials);ids=[]
        for i,s in enumerate(slots):
            label=canon(s.material_slot_name)
            if 'factorycompensator' in label:s.material_interface=metal
            else:
                if label not in original:raise RuntimeError('Preserve existing native material: unknown new slot '+label)
                s.material_interface=original[label]
            if 'manny' in label:ids.append(i)
            slots[i]=s
        body.set_editor_property('materials',slots)
        if sub:
            for lod in range(sub.get_lod_count(body)):
                settings=sub.get_lod_build_settings(body,lod);settings.use_full_precision_u_vs=True;sub.set_lod_build_settings(body,lod,settings)
        E.set_metadata_tag(body,'PitViperSourceSHA256',entry['sha256'])
        E.set_metadata_tag(body,'FactoryCompensatorSection','M_PitViper2011_FactoryCompensator')
        save(body);save(body.skeleton)
        arm_ids[body.get_path_name()]=ids
        receipt['families'][key]={'asset':body.get_path_name(),'skeleton':body.skeleton.get_path_name(),'source':entry['fbx'],
           'factory_material_slot':'M_PitViper2011_FactoryCompensator','source_triangles':entry['factory_compensator_triangles']};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
library=load(WET);mapping=dict(library.get_editor_property('wet_materials'))
for material in bindings.values():mapping[material.get_path_name()]=material
library.set_editor_property('wet_materials',mapping);save(library)
# Native arm material slot numbers can move when adding a gun-only section.
# Change only the three existing profile fields, leaving their outfits intact.
path=P/'Content/ColdSteelData/modular_outfits.json';text=path.read_text(encoding='utf-8-sig')
start=text.index('{',text.index('"profiles"'));profiles,size=json.JSONDecoder().raw_decode(text[start:])
for key,ids in arm_ids.items():
    if key in profiles:profiles[key]['hide_source_materials']=ids
if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Preserve concurrent outfit changes')
path.write_text(text[:start]+json.dumps(profiles,ensure_ascii=False,indent=2)+text[start+size:],encoding='utf8')
receipt.update(status='imported_and_saved',native_code_required=True,animations_imported=False,catalog_published=False)
record();print('PIT_VIPER_SI_COMPENSATOR_ASSETS_IMPORTED_AND_SAVED',flush=True)
finish=O.parent/'PitViper2011SurfaceRefine20261003/restore_saved_finish.py'
if finish.exists():
    import runpy
    runpy.run_path(str(finish),run_name='__main__')
