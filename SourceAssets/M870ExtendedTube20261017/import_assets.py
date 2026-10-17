"""Save the cosmetic extension; partition only the native front disk material IDs."""
import unreal as u
import json, hashlib, shutil, re
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
D='/Game/Weapons/M870/ExtendedTube20261017'
NATIVE='/Game/Weapons/M870/Tactical20261015/SK_M870_V7'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
R={'completed':False,'saved':[],'runtime_tested':False}
def record():(O/'import_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
    R['saved'].append(obj.get_path_name());record()
command=u.SystemLibrary.get_command_line().lower()
if '-run=pythonscript' in command:
    if '-allowcommandletrendering' not in command:raise RuntimeError('Mesh authoring needs the rendering commandlet')
elif u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before changing the native material group')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if NATIVE in dirty or any(p.startswith(D+'/') for p in dirty):raise RuntimeError('Preserve unsaved target packages')
native=load(NATIVE);source_hash=hashlib.sha256(disk(NATIVE).read_bytes()).hexdigest()
has_cap=any(str(s.material_slot_name)=='M870_FactoryTubeCap' for s in native.materials)
author=json.loads((O/'authoring_receipt.json').read_text())
if not has_cap and source_hash!=author['native_sha256']:raise RuntimeError('Native changed since extension authoring; preserve current gun')

cap_path=D+'/Materials/M_M870_ExtTube_NativeCap'
cap=load(cap_path) if E.does_asset_exist(cap_path) else E.duplicate_asset('/Game/Weapons/M870/Tactical20261015/Materials/M_M870_OriginalSurface',cap_path)
if not cap:raise RuntimeError('Cannot duplicate original cap surface')
cap.set_editor_property('automatically_set_usage_in_editor',False)
for prop in ('used_with_skeletal_mesh','used_with_clothing','used_with_morph_targets'):cap.set_editor_property(prop,False)
u.MaterialEditingLibrary.recompile_material(cap);save(cap)
coat=load('/Game/Weapons/M870/Optics20261016/Materials/M_M870_AdapterSteel')
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
    imp.import_mesh_lods=True;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(O/'Exports/SM_M870_ExtendedTube_Lods.fbx')
    task.destination_path=D+'/Meshes';task.destination_name='SM_M870_ExtendedTube';task.automated=True
    task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opt
    A.import_asset_tasks([task]);mesh=load(D+'/Meshes/SM_M870_ExtendedTube')
    slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):
        key=re.sub(r'(?:\.\d+|_\d+)$','',str(slot.material_slot_name))
        mat={'M870_ExtTube_Coat':coat,'M870_ExtTube_NativeCap':cap}.get(key)
        if not mat:raise RuntimeError('Unbound extension material '+key)
        slot.material_interface=mat;slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
    ed=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    for level in range(ed.get_lod_count(mesh)):
        settings=ed.get_lod_build_settings(mesh,level)
        settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True
        settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True;settings.generate_lightmap_u_vs=False
        ed.set_lod_build_settings(mesh,level,settings)
    if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):raise RuntimeError('Static mesh build did not finish')
    E.set_metadata_tag(mesh,'M870TubeSource',str(O/'authoring_receipt.json'))
    E.set_metadata_tag(mesh,'M870TubeMount','Native component bind centimetres; WPN_root; full inverse bind transform')
    save(mesh);R['mesh']={'asset':mesh.get_path_name(),'lods':ed.get_lod_count(mesh),'materials':[s.material_interface.get_path_name() for s in slots]};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

if not has_cap:
    dm,status=G.copy_mesh_from_skeletal_mesh(native,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native mesh')
    _,positions,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
    positions=u.GeometryScript_List.convert_vector_list_to_array(positions)
    _,triangles,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)
    triangles=u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    slots=[s.copy() for s in native.materials];original_count=len(slots)
    source=next(i for i,s in enumerate(slots) if str(s.material_slot_name)=='M870_OriginalSurface')
    selected=[]
    for tid,t in enumerate(triangles):
        if u.GeometryScript_Materials.get_triangle_material_id(dm,tid)[0]!=source:continue
        if all(-positions[v].y>=46 and -77.4<positions[v].z<-74.7 for v in (t.x,t.y,t.z)):selected.append(tid)
    if len(selected)!=24:raise RuntimeError('Native cap selection differs; leave gun unchanged: '+str(len(selected)))
    new=slots[source].copy();new.material_slot_name='M870_FactoryTubeCap';slots.append(new)
    before=O/'Before/SK_M870_V7.uasset';before.parent.mkdir(exist_ok=True)
    if not before.exists():shutil.copy2(disk(NATIVE),before)
    for tid in selected:u.GeometryScript_Materials.set_triangle_material_id(dm,tid,original_count)
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,
        use_original_vertex_order=True,replace_materials=True,new_materials=[s.material_interface for s in slots],
        new_material_slot_names=[s.get_editor_property('imported_material_slot_name') for s in slots[:original_count]]+['M870_FactoryTubeCap'],
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,native,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write cap material section')
    # The copy options preserve imported names (read-only in Python). Restore the
    # separate display labels, including the established arm and furniture slots.
    created=list(native.materials)
    for i,slot in enumerate(slots):
        created[i].material_slot_name=slot.material_slot_name
        created[i].material_interface=slot.material_interface
    native.set_editor_property('materials',created);save(native)
    R['native_cap']={'triangles':len(selected),'source_sha256':source_hash,
        'saved_sha256':hashlib.sha256(disk(NATIVE).read_bytes()).hexdigest(),
        'operation':'24 front disk material IDs only; retained vertex data, skin weights, skeleton, UVs and animation assets'}
else:R['native_cap']={'operation':'Existing cap group retained','source_sha256':source_hash}
R['completed']=True;record();print('M870_EXTENDED_TUBE_ASSETS_SAVED',flush=True)
