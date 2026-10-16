"""Import the extended-tube set and partition only the native cap material group.

All geometry is cosmetic game artwork. Preserve the current native skeleton,
skin weights, geometry, UVs, normals and existing stock/grip material groups.
"""
import unreal as u
import json,shutil,hashlib,re
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
D='/Game/Weapons/Super90/ExtendedTube20261015'
NATIVE='/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
R={'complete':False,'saved':[],'meshes':{},'runtime_tested':False}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    R['saved'].append(obj.get_path_name());record()
command=u.SystemLibrary.get_command_line().lower()
if '-run=pythonscript' in command:
    if '-allowcommandletrendering' not in command:raise RuntimeError('Use RHI commandlet for mesh build data')
elif u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before asset import')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if NATIVE in dirty or any(p.startswith(D+'/') for p in dirty):
    raise RuntimeError('Target asset has unsaved editor changes; preserve current package')
native=load(NATIVE)
native_steel=load('/Game/Weapons/Super90/WS1Surface20261007/Materials/MI_Super90_S90_BarrelSteel')
steel_path=D+'/Materials/MI_S90_ExtTube_Steel'
steel=load(steel_path) if E.does_asset_exist(steel_path) else E.duplicate_asset(native_steel.get_path_name(),steel_path)
if not steel:raise RuntimeError('Cannot create tube finish')
for key,value in {'SourceColorWeight':0,'SourceRoughnessWeight':0,'Roughness':.42,
                  'GrainRoughness':0,'MottleRoughness':0,'MottleColor':0,'EdgeWear':0,
                  'EdgeBreakup':0,'ScratchAmount':0,'HandlingPolish':0,'CavityDarken':0,
                  'CavityRoughness':0,'Stipple':0,'MaskUVChannel':0}.items():
    L.set_material_instance_scalar_parameter_value(steel,key,value)
for key,path in {'SurfaceNormal':'/Game/Weapons/CommonShotgun/Choke20261015/Textures/T_Choke_FlatNormal',
                 'SurfaceMask':'/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral',
                 'SourceRoughness':'/Game/Weapons/WeaponSurface/Textures/T_WS_GreyLinear'}.items():
    L.set_material_instance_texture_parameter_value(steel,key,load(path))
L.update_material_instance(steel);save(steel)
specs=[('SM_Super90_ExtendedTube',None,None),
       ('SM_Super90_ChokeTubeFit','/Game/Weapons/CommonShotgun/Choke20261015',24.8),
       ('SM_Super90_SuppressorTubeFit','/Game/Weapons/CommonShotgun/Suppressor20261015',27.8)]
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for name,material_root,tip in specs:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False
        opt.import_textures=False;opt.import_animations=False
        imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False
        imp.generate_lightmap_u_vs=False;imp.import_mesh_lo_ds=True
        imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=str(O/'Exports'/(name+'_Lods.fbx'))
        task.destination_path=D+'/Meshes';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        task.factory=u.FbxFactory();task.options=opt;A.import_asset_tasks([task])
        mesh=load(D+'/Meshes/'+name);slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            key=re.sub(r'(?:\.\d+|_\d+)$','',str(slot.material_slot_name))
            if material_root:mat=load(material_root+'/Materials/MI_'+key)
            else:
                mat={'S90_ExtTube_NativeCap':native_steel,'S90_ExtTube_Steel':steel}.get(key)
                if not mat:raise RuntimeError('Unknown tube material '+key)
            slot.material_interface=mat;slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
        sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        for level in range(sms.get_lod_count(mesh)):
            settings=sms.get_lod_build_settings(mesh,level)
            settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True
            settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True
            settings.generate_lightmap_u_vs=False;sms.set_lod_build_settings(mesh,level,settings)
        if tip is not None:
            for socket_name,x in [('Mount',0),('Muzzle',tip),('AimGuide',tip+1)]:
                socket=mesh.find_socket(socket_name)
                if not socket:
                    socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',socket_name);mesh.add_socket(socket)
                socket.set_editor_property('relative_location',u.Vector(x,0,0))
        if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):raise RuntimeError('Mesh build incomplete '+name)
        E.set_metadata_tag(mesh,'Super90ExtendedTubeSource',str(O/'authoring_receipt.json'))
        save(mesh)
        R['meshes'][name]={'asset':mesh.get_path_name(),'lods':sms.get_lod_count(mesh),
            'materials':[s.material_interface.get_path_name() for s in slots],'muzzle_socket_cm':tip}
        record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

# Find whole native cap islands using shared edges and coincident positions.
# Weld is used for selection only: no native vertices are moved or merged.
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
dm,status=G.copy_mesh_from_skeletal_mesh(native,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native cap geometry')
_,positions,_=Q.get_all_vertex_positions(dm,False);positions=u.GeometryScript_List.convert_vector_list_to_array(positions)
_,triangles,_=Q.get_all_triangle_indices(dm,False);triangles=u.GeometryScript_List.convert_triangle_list_to_array(triangles)
points=[(v.x,-v.y,v.z) for v in positions] # x, forward, up in native UE centimetres
parent=list(range(len(points)))
def find(a):
    while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
    return a
def union(a,b):
    a=find(a);b=find(b)
    if a!=b:parent[b]=a
coincident={}
for i,p in enumerate(points):
    key=tuple(round(c,4) for c in p)
    if key in coincident:union(i,coincident[key])
    else:coincident[key]=i
for t in triangles:union(t.x,t.y);union(t.x,t.z)
groups={}
for i,t in enumerate(triangles):groups.setdefault(find(t.x),[]).append(i)
selected=[];islands=[]
for ids in groups.values():
    vertices={v for i in ids for v in (triangles[i].x,triangles[i].y,triangles[i].z)}
    mn=[min(points[v][k] for v in vertices) for k in range(3)]
    mx=[max(points[v][k] for v in vertices) for k in range(3)]
    if mn[1]>47.4 and mx[1]<50.1 and mn[2]>-79 and mx[2]<-75.7:
        selected.extend(ids);islands.append({'triangles':len(ids),'bounds_forward_cm':[mn,mx]})
if len(selected)!=1996 or len(islands)!=2:
    raise RuntimeError('Native cap topology differs from authored source; preserve current gun: '+str(islands))
slots=[s.copy() for s in native.materials];original_count=len(slots);remap={};changed=0
for tid in selected:
    old=u.GeometryScript_Materials.get_triangle_material_id(dm,tid)[0]
    if str(slots[old].material_slot_name).startswith('S90_FactoryTubeCap_'):continue
    if slots[old].material_interface!=native_steel:raise RuntimeError('Cap source material changed; preserve native gun')
    if old not in remap:
        name='S90_FactoryTubeCap_'+str(slots[old].material_slot_name)
        existing=next((i for i,s in enumerate(slots) if str(s.material_slot_name)==name),None)
        if existing is None:
            slot=slots[old].copy();slot.material_slot_name=name;existing=len(slots);slots.append(slot)
        remap[old]=existing
    u.GeometryScript_Materials.set_triangle_material_id(dm,tid,remap[old]);changed+=1
before=hashlib.sha256(disk(NATIVE).read_bytes()).hexdigest()
if changed:
    backup=O/'Before/SK_Super90_V7.uasset';backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(disk(NATIVE),backup)
    names=[s.get_editor_property('imported_material_slot_name') for s in slots[:original_count]]+[str(s.material_slot_name) for s in slots[original_count:]]
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,
        use_original_vertex_order=True,replace_materials=True,new_materials=[s.material_interface for s in slots],
        new_material_slot_names=names,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,native,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write cap material group')
    created=list(native.materials)
    for i in range(original_count,len(slots)):
        created[i].material_slot_name=slots[i].material_slot_name;created[i].material_interface=slots[i].material_interface;slots[i]=created[i]
    native.set_editor_property('materials',slots);save(native)
R['native_cap']={'islands':islands,'changed_triangles':changed,'source_sha256':before,
    'saved_sha256':hashlib.sha256(disk(NATIVE).read_bytes()).hexdigest(),
    'operation':'material IDs only; original geometry, UV, normals, skin and skeleton retained'};record()
icon_name='magazine_super90_extended_tube';icon_file=O/(icon_name+'.png')
canonical=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/(icon_name+'.png')
shutil.copy2(icon_file,canonical)
for destination,name in [('/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms',icon_name),(D+'/UI','T_Super90ExtendedTube_Icon')]:
    task=u.AssetImportTask();task.filename=str(icon_file);task.destination_path=destination;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory();A.import_asset_tasks([task])
    icon=load(destination+'/'+name);icon.lod_group=u.TextureGroup.TEXTUREGROUP_UI
    icon.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;icon.srgb=True;icon.never_stream=True
    E.set_metadata_tag(icon,'Icon.SourceRecipe',str(O/'generation_prompts.json'));save(icon)
R['complete']=True;record();print('SUPER90_EXTENDED_TUBE_ASSETS_SAVED',flush=True)
