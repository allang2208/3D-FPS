"""Save fitted furniture, sparse grip layers and the reversible factory section."""
import unreal as u,json,hashlib,shutil,re,runpy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/M870/CommonFurniture20261016'
C=json.loads((O/'inputs.json').read_text());M=json.loads((O/'models.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
R=json.loads((O/'install_receipt.json').read_text()) if globals().get('ONLY_PARTS') else {'saved':[],'meshes':{},'profiles':{},'runtime_tested':False}
R['completed']=False
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing '+p)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    if a.get_path_name() not in R['saved']:R['saved'].append(a.get_path_name())
    record();return a
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
native_path=C['assets']['m870']['path'];native=load(native_path)
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Stop PIE before saving')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
resuming={D+'/Meshes/SM_M870_'+key for key in globals().get('RESUME_IMPORTED',())}
if native_path in dirty or any(p.startswith(D+'/') and p not in resuming for p in dirty):raise RuntimeError('Preserve unsaved target assets')
factory=next((i for i,s in enumerate(native.materials) if str(s.material_slot_name)=='M870_FactoryFurniture'),None)
if factory is None and sha(native_path)!=C['assets']['m870']['sha256']:raise RuntimeError('Native M870 changed since extraction; preserve current asset')
if any(row.get('revision')=='RearGripFinish' and (not globals().get('ONLY_PARTS') or key in ONLY_PARTS) for key,row in M['parts'].items()):
    runpy.run_path(str(O/'RearGripFinish/materials.py'))
    material_receipt=json.loads((O/'RearGripFinish/material_receipt.json').read_text())
    for path in material_receipt['saved']:
        if path not in R['saved']:R['saved'].append(path)
    R['rear_grip_finish_materials']=material_receipt['saved']
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,part in M['parts'].items():
        if globals().get('ONLY_PARTS') and key not in ONLY_PARTS:continue
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
        imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS if part.get('explicit_tangents') else u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        imp.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=part['file'];task.destination_path=D+'/Meshes';task.destination_name='SM_M870_'+key
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opt
        target=task.destination_path+'/'+task.destination_name
        # Legacy FBX reimport can prefer the asset's saved import data over the
        # task UI. Persist the authored basis contract before it rebuilds LOD0.
        if part.get('explicit_tangents') and E.does_asset_exist(target):
            existing=load(target)
            existing.get_editor_property('asset_import_data').set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
        if key not in globals().get('RESUME_IMPORTED',()):A.import_asset_tasks([task])
        mesh=load(target);slots=list(mesh.static_materials)
        if part.get('explicit_tangents'):
            mesh.get_editor_property('asset_import_data').set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
        for i,slot in enumerate(slots):
            label=str(slot.get_editor_property('imported_material_slot_name'))
            # FBX sanitizes Blender's duplicate-material suffix .001 to _001.
            bindings={k.replace('.','_'):v for k,v in part['bindings'].items()}
            source=bindings.get(label) or bindings.get(re.sub(r'_\d{3}$','',label))
            if not source:raise RuntimeError('Unbound material '+key+' '+label)
            slot.material_slot_name=label;slot.material_interface=load(source);slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        donor=load(part['source'])
        if isinstance(donor,u.StaticMesh):mesh.set_editor_property('nanite_settings',donor.get_editor_property('nanite_settings'))
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
        ed=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        settings=ed.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=not part.get('explicit_tangents',False);settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True
        ed.set_lod_build_settings(mesh,0,settings)
        E.set_metadata_tag(mesh,'M870FurnitureSource',part['source'])
        E.set_metadata_tag(mesh,'M870FurnitureBind','Component bind centimetres; WPN_bolt for pump grips; WPN_root for rear furniture')
        save(mesh);R['meshes'][key]=mesh.get_path_name();record()
    for family in ('vertical','canted','prism','angled'):
        if globals().get('ONLY_PARTS'):continue
        name='DA_M870_'+family;path=D+'/Profiles/'+name
        if E.does_asset_exist(path):asset=load(path)
        else:
            factory_data=u.DataAssetFactory();factory_data.set_editor_property('data_asset_class',u.WeaponGripProfile)
            asset=A.create_asset(name,D+'/Profiles',u.WeaponGripProfile,factory_data)
        if not asset.set_shared_clips_from_json((O/'Profiles'/(family+'.json')).read_text()):raise RuntimeError('Grip profile import failed '+family)
        E.set_metadata_tag(asset,'M870FurnitureSource','Existing common left grasp; latest M870LeftArm20261016 source; pump-driven contact; native loading and trigger hand untouched')
        save(asset);R['profiles'][family]=asset.get_path_name();record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
if factory is None:
    backup=O/'Before/SK_M870_V7.uasset';backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(disk(native_path),backup)
    slots=[s.copy() for s in native.materials];original=len(slots)
    source=next(i for i,s in enumerate(slots) if 'M_M870_OriginalSurface' in s.material_interface.get_path_name())
    slot=slots[source].copy();slot.material_slot_name='M870_FactoryFurniture';slots.append(slot)
    dm,status=G.copy_mesh_from_skeletal_mesh(native,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native extraction failed')
    ids=json.loads((O/'factory_triangles.json').read_text())
    for i in ids:u.GeometryScript_Materials.set_triangle_material_id(dm,i,original)
    names=[s.get_editor_property('imported_material_slot_name') for s in slots[:original]]+['M870_FactoryFurniture']
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,use_original_vertex_order=True,replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=names,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,native,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save factory grouping')
    created=list(native.materials)
    # GeometryScript uses imported names when rebuilding the material table.
    # Retain the original semantic display slots, including Manny arm sections.
    for index in range(original):created[index].material_slot_name=slots[index].material_slot_name
    created[original].material_slot_name='M870_FactoryFurniture';created[original].material_interface=slot.material_interface
    native.set_editor_property('materials',created);E.set_metadata_tag(native,'M870FurnitureGroups','20261016');save(native)
    R['factory_group']={'triangles':len(ids),'before_sha256':C['assets']['m870']['sha256'],'saved_sha256':sha(native_path)}
else:R.setdefault('factory_group',{}).update(already_installed=True,slot=factory)
R['completed']=True;record();print('M870_FURNITURE_SAVED',len(R['meshes']),len(R['profiles']),flush=True)
