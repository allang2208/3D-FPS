"""Save independent V11 actions and fitted mechanical sight; no PIE or live switching."""
import json, hashlib
from pathlib import Path
import unreal as u
P=Path(__file__).parent;DEST='/Game/Weapons/DarkBow20260925/SightContactV11'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt_path=P/'import-receipt.json'
r=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'saved':{},'runtime_tested':False}
r.setdefault('source_hashes',{})
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
if dirty:raise RuntimeError('Preserve unsaved candidate packages '+str(dirty))
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    r['saved'][asset.get_name()]=asset.get_path_name()
    receipt_path.write_text(json.dumps(r,indent=2),encoding='utf8')
def fresh(name):
    if name not in r['saved'] and E.does_asset_exist(DEST+'/'+name):raise RuntimeError('Unowned existing asset '+name)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
mesh=u.load_asset('/Game/Weapons/DarkBow20260925/ContactV9/SK_Bow_BareArmsV7')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
info=json.loads((P/'authoring.json').read_text())
for role in info['durations']:
    name='A_Bow_'+role
    source=P/'Export'/(name+'.fbx');source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    if name in r['saved'] and r['source_hashes'].get(name)==source_hash:continue
    fresh(name);opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=mesh.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['fps'])
    opt.anim_sequence_import_data.set_editor_property('remove_redundant_keys',False)
    task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=name in r['saved'];task.save=False;task.options=opt;A.import_asset_tasks([task])
    asset=u.load_asset(DEST+'/'+name)
    if not asset:raise RuntimeError('Import missing '+name)
    if compression:asset.set_editor_property('bone_compression_settings',compression)
    asset.set_preview_skeletal_mesh(mesh)
    if hashlib.sha256(source.read_bytes()).hexdigest()!=source_hash:raise RuntimeError('FBX changed during import '+name)
    r['source_hashes'][name]=source_hash;save(asset)
materials=[]
for name,color,metal,rough,glow in [('M_BowSight_BlackSteel',(.025,.034,.042),.82,.34,0),
    ('M_BowSight_Brass',(.24,.13,.035),.8,.31,0),('M_BowSight_Fiber',(.20,.85,.38),0,.26,1.2)]:
    if name in r['saved']:materials.append(u.load_asset(r['saved'][name]));continue
    fresh(name);mat=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    vec=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
    vec.constant=u.LinearColor(*color,1);L.connect_material_property(vec,'',u.MaterialProperty.MP_BASE_COLOR)
    for val,prop in [(metal,u.MaterialProperty.MP_METALLIC),(rough,u.MaterialProperty.MP_ROUGHNESS)]:
        node=L.create_material_expression(mat,u.MaterialExpressionConstant);node.r=val;L.connect_material_property(node,'',prop)
    if glow:
        node=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
        node.constant=u.LinearColor(*(c*glow for c in color),1);L.connect_material_property(node,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.recompile_material(mat);save(mat);materials.append(mat)
name='SM_Bow_OpenMechanicalSight'
if name not in r['saved']:
    fresh(name);opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False;opt.static_mesh_import_data.combine_meshes=True
    opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False;task.options=opt;A.import_asset_tasks([task])
    asset=u.load_asset(DEST+'/'+name)
    if not asset:raise RuntimeError('Sight import missing')
    slots=list(asset.static_materials)
    for slot in slots:
        label=str(slot.material_slot_name)
        slot.material_interface=materials[2 if 'Fiber' in label else 1 if 'Brass' in label else 0]
    asset.static_materials=slots
    b=asset.get_bounds();r['sight_size_cm']=[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2]
    if not (15<r['sight_size_cm'][1]<25):raise RuntimeError('Sight FBX unit/axis mismatch '+str(r['sight_size_cm']))
    save(asset)
# Authoring interface check: the real imported fibre centre must stay in the
# same riser-local coordinates used by ADS, including the FBX handedness.
asset=u.load_asset(r['saved']['SM_Bow_OpenMechanicalSight'])
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read imported sight interface')
Q=u.GeometryScript_MeshQueries
_,vlist,_=Q.get_all_vertex_positions(dm,False);verts=u.GeometryScript_List.convert_vector_list_to_array(vlist)
_,tlist,_=Q.get_all_triangle_indices(dm,False);triangles=u.GeometryScript_List.convert_triangle_list_to_array(tlist)
fiber=next(i for i,s in enumerate(asset.static_materials) if 'Fiber' in str(s.material_slot_name))
ids=set()
for i,t in enumerate(triangles):
    if u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0]==fiber:ids.update([t.x,t.y,t.z])
pin=[sum(getattr(verts[i],axis) for i in ids)/len(ids) for axis in ['x','y','z']]
r['imported_pin_center_cm']=pin
if max(abs(x-y) for x,y in zip(pin,[-3.5,-13.9,14.6]))>.08:raise RuntimeError('Imported pin axis mismatch '+str(pin))
receipt_path.write_text(json.dumps(r,indent=2),encoding='utf8')
print('BOW_SIGHT_V11_SAVED',json.dumps(r))
