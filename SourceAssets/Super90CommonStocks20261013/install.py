"""Import/save Super90 stocks, finishes and factory-only material sections."""
import unreal as u
import json,math,hashlib,shutil,gzip
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D='/Game/Weapons/Super90/CommonStocks20261013'
C=json.loads((O/'inputs.json').read_text());M=json.loads((O/'models.json').read_text())
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt=O/'install_receipt.json'
R=json.loads(receipt.read_text()) if receipt.exists() else {'saved':[],'meshes':{},'materials':{},'runtime_tested':False}
R['complete']=False
def record():receipt.write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
    if obj.get_path_name() not in R['saved']:R['saved'].append(obj.get_path_name())
    record();return obj
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Stop PIE before stock asset saves')
native_path=C['assets']['super90']['path'];native=load(native_path)
if native_path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Native Super90 has unsaved changes')
factory_names={'S90_FactoryStock_'+C['assets']['super90']['slots'][i]['name'] for i in (4,9,10)}
existing_factory={str(s.material_slot_name) for s in native.materials if str(s.material_slot_name).startswith('S90_FactoryStock_')}
if existing_factory and existing_factory!=factory_names:raise RuntimeError('Incomplete stock groups; preserve current package')
has_factory=existing_factory==factory_names
if not has_factory and sha(native_path)!=C['assets']['super90']['sha256']:
    raise RuntimeError('Native Super90 changed since extraction; preserve current package')
master=load('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface')
def material(name,kind='metal',normal=None,rough=None,scale=30,native_copy=False):
    path=D+'/Materials/MI_'+name
    mi=load(path) if E.does_asset_exist(path) else A.create_asset('MI_'+name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,master)
    if native_copy:
        source=C['materials'][C['assets']['super90']['slots'][10]['material']]
        for k,v in source['scalars'].items():L.set_material_instance_scalar_parameter_value(mi,k,v)
        for k,v in source['vectors'].items():L.set_material_instance_vector_parameter_value(mi,k,u.LinearColor(*v))
        for k,v in source['textures'].items():
            if v:L.set_material_instance_texture_parameter_value(mi,k,load(v))
    else:
        color,metallic,r={'metal':((.020,.021,.022),1,.46),'polymer':((.019,.019,.018),0,.55),'rubber':((.0103,.0103,.0103),0,.70)}[kind]
        values={'SourceColorWeight':0,'SourceRoughnessWeight':.05 if rough else 0,'Roughness':r,'Metallic':metallic,'GrainTileCm':2,'GrainRoughness':.012,'MottleRoughness':.005,'MottleColor':0,'EdgeWear':0,'EdgeBreakup':0,'ScratchAmount':0,'HandlingPolish':0,'CavityDarken':0,'CavityRoughness':0,'Stipple':0,'MaskUVChannel':0,'WeaponWetness':0,'BeadScale':scale}
        for k,v in values.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
        L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*color,1))
        L.set_material_instance_texture_parameter_value(mi,'SurfaceNormal',load(normal or '/Engine/EngineMaterials/DefaultNormal'))
        L.set_material_instance_texture_parameter_value(mi,'SurfaceMask',load('/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral'))
        L.set_material_instance_texture_parameter_value(mi,'SourceRoughness',load(rough or '/Game/Weapons/WeaponSurface/Textures/T_WS_GreyLinear'))
    L.update_material_instance(mi);save(mi);R['materials'][name]=mi.get_path_name();record();return mi
neck=material('Super90_StockNativePolymer',native_copy=True)
adapter=material('Super90_StockAdapterMetal',scale=10)
texture_sets={
    'core_stock':('/Game/Weapons/CoreStock20260914/Meshy0914005605/Textures/T_CoreStock_Normal_Game','/Game/Weapons/CoreStock20260914/Meshy0914005605/Textures/T_CoreStock_Roughness'),
    'qr_performance':('/Game/Weapons/QRPerformanceStock/Meshy20260913/Textures/T_Stock_Normal','/Game/Weapons/QRPerformanceStock/Meshy20260913/Textures/T_Stock_Roughness'),
    'tactical_telescopic':('/Game/Weapons/TacticalTelescopicStock20260914/Textures/T_TacticalStock_Normal_Game','/Game/Weapons/TacticalTelescopicStock20260914/Textures/T_TacticalStock_Roughness')}
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,row in M['parts'].items():
        bindings={}
        for i,name in enumerate(row['slots']):
            if name.startswith('S90_StockNativePolymer'):bindings[name]=neck;continue
            if name.startswith('S90_StockAdapterMetal'):bindings[name]=adapter;continue
            spec=row['bindings'][name];slot=spec['name']
            # Keep intentional champagne trim and the red inset; steel and body
            # metal receive this gun's clean dark finish rather than M4's atlas.
            if slot in ('Stock_Champagne','Stock_RedInset'):
                bindings[name]=load(spec['material']);continue
            kind='rubber' if 'Rubber' in slot else 'polymer' if 'Polymer' in slot or slot=='CoreStockBody' else 'metal'
            normal,rough=texture_sets.get(key,(None,None))
            if 'Adapter' in slot:normal=rough=None
            if key=='legendary_adjustable_tactical_stock':
                normal='/Game/Weapons/LegendaryStock20261006/Textures/T_TacticalStock_'+('Rubber' if kind=='rubber' else 'Metal' if slot=='Stock_Steel' else 'Coating')+'_N'
            area,uvarea=row['area_cm2_uv'].get(str(i),[0,0]);scale=math.sqrt(area/uvarea)/.42 if uvarea>1e-8 else 10
            bindings[name]=material('Super90_'+key+'_'+str(i),kind,normal,rough,scale)
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
        imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;imp.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=row['file'];task.destination_path=D+'/Meshes';task.destination_name='SM_Super90_'+key
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opt
        A.import_asset_tasks([task]);mesh=load(task.destination_path+'/'+task.destination_name)
        mesh.set_editor_property('nanite_settings',load(row['source']).get_editor_property('nanite_settings'))
        slots=list(mesh.static_materials)
        for i,s in enumerate(slots):s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
        mesh.set_editor_property('static_materials',slots);u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
        ed=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        settings=ed.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=True
        settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True;ed.set_lod_build_settings(mesh,0,settings)
        E.set_metadata_tag(mesh,'Super90StockSource',row['source']+'; native front neck + closed 23.2 mm rod; component bind cm')
        save(mesh);bounds=mesh.get_bounding_box()
        R['meshes'][key]={'path':mesh.get_path_name(),'saved':True,'bounds_cm':[[bounds.min.x,bounds.min.y,bounds.min.z],[bounds.max.x,bounds.max.y,bounds.max.z]],'materials':[s.material_interface.get_path_name() for s in slots]};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

# Group assignment is idempotent and repairs the original broad selection:
# only the connected stock polymer island belongs to the replacement.
backup=O/'Before/SK_Super90_V7.uasset';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(disk(native_path),backup)
if has_factory:
    repair_backup=O/'Before/SelectionRepair/SK_Super90_V7.uasset';repair_backup.parent.mkdir(parents=True,exist_ok=True)
    if not repair_backup.exists():shutil.copy2(disk(native_path),repair_backup)
slots=[s.copy() for s in native.materials];original_count=len(slots);remap={}
for i in (4,9,10):
    name='S90_FactoryStock_'+str(slots[i].material_slot_name)
    if has_factory:remap[i]=next(j for j,slot in enumerate(slots) if str(slot.material_slot_name)==name)
    else:
        slot=slots[i].copy();slot.material_slot_name=name;remap[i]=len(slots);slots.append(slot)
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
mesh_data,status=G.copy_mesh_from_skeletal_mesh(native,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native stock groups')
with gzip.open(O/'Inputs/native_geometry.json.gz','rt') as f:baseline=json.load(f)
_,indices,_=Q.get_all_triangle_indices(mesh_data,False);indices=u.GeometryScript_List.convert_triangle_list_to_array(indices)
if [[t.x,t.y,t.z] for t in indices]!=baseline['triangles']:raise RuntimeError('Native topology changed; preserve current package and remeasure selection')
triangles=set(json.loads((O/'factory_triangles.json').read_text()));reverse={v:k for k,v in remap.items()};changed=0;restored=0
for i in range(len(indices)):
    old=u.GeometryScript_Materials.get_triangle_material_id(mesh_data,i)[0]
    target=remap[baseline['materials'][i]] if i in triangles else reverse.get(old,old)
    if old!=target:
        u.GeometryScript_Materials.set_triangle_material_id(mesh_data,i,target);changed+=1
        if i not in triangles:restored+=1
if changed:
    names=[s.get_editor_property('imported_material_slot_name') for s in slots[:original_count]]+[str(s.material_slot_name) for s in slots[original_count:]]
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,use_original_vertex_order=True,replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=names,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(mesh_data,native,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write native stock material groups')
    created=list(native.materials)
    for i in range(original_count,len(slots)):
        created[i].material_slot_name=slots[i].material_slot_name;created[i].material_interface=slots[i].material_interface;slots[i]=created[i]
    native.set_editor_property('materials',slots);save(native)
R['factory_section']={'faces':len(triangles),'selection':'connected_stock_polymer_island','changed_faces_this_run':changed,'non_stock_faces_restored_this_run':restored,'before_sha256':C['assets']['super90']['sha256'],'saved_sha256':sha(native_path),'geometry_weights_uv_skeleton_animations_edited':False};record()

icon_name='ue_super90_stock_false';icon_dir=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
shutil.copy2(O/(icon_name+'.png'),icon_dir/(icon_name+'.png'))
task=u.AssetImportTask();task.filename=str(icon_dir/(icon_name+'.png'));task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms';task.destination_name=icon_name
task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
icon=load(task.destination_path+'/'+icon_name);icon.srgb=True;icon.lod_group=u.TextureGroup.TEXTUREGROUP_UI
icon.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;icon.never_stream=True;icon.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;save(icon)
R['complete']=True;record();print('SUPER90_COMMON_STOCKS_SAVED',len(R['meshes']),len(R['saved']))
