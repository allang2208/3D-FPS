"""Save the six new fitted straps; retain the accepted Nanite pouch and textures."""
import gc,hashlib,importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SimpleSlingBag20261022/GravityFitR3'
DEST='/Game/Characters/SimpleSlingBag20261022/GravityFitR3';OLD='/Game/Characters/SimpleSlingBag20261022'
E,G,L=u.EditorAssetLibrary,u.GeometryScript_AssetUtils,u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
plan=json.loads((R/'manifest.json').read_text());saved={'revision':plan['revision'],'variants':{},'materials':{},'runtime_tested':False}
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('gravity_sling_io',P/'Tools/ChainmailPants/save_assets.py')
winding=module('gravity_sling_winding',P/'Tools/BackpackHarness/winding.py')
motion=module('gravity_sling_mask',P/'Tools/BackpackMotion/save_assets.py')
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside gravity-fit asset scope')
    asset.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):
        raise RuntimeError('Cannot save gravity-fit asset')
def receipt():
    (R/'saved_assets.json').write_text(json.dumps(saved,indent=2))
def gravity_normal(mat):
    if E.get_metadata_tag(mat,'SlingGravityNormals')=='R3':return
    def node(kind,**properties):
        result=L.create_material_expression(mat,kind)
        for key,value in properties.items():result.set_editor_property(key,value)
        return result
    def wire(source,target,pin,output=''):
        if not L.connect_material_expressions(source,output,target,pin):raise RuntimeError('Cannot connect sling normal '+pin)
    normal=L.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL)
    output=L.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_NORMAL) if normal else ''
    tangent=mat.get_editor_property('tangent_space_normal')
    if not normal:
        normal=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1)) if tangent else node(u.MaterialExpressionVertexNormalWS)
    if tangent:
        world=node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        wire(normal,world,str(L.get_material_expression_input_names(world)[0]),output);normal=world;output=''
    rotated=node(u.MaterialExpressionCustom,description='Sling gravity normal',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
        code='return normalize(N + saturate(Mask)*float3(dot(RowX,N),dot(RowY,N),dot(RowZ,N)));')
    inputs=[]
    for name in ['N','Mask','RowX','RowY','RowZ']:
        entry=u.CustomInput();entry.set_editor_property('input_name',name);inputs.append(entry)
    rotated.set_editor_property('inputs',inputs);wire(normal,rotated,'N',output)
    color=node(u.MaterialExpressionVertexColor);wire(color,rotated,'Mask','R')
    for i,name in enumerate(['RowX','RowY','RowZ']):
        parameter=node(u.MaterialExpressionVectorParameter,parameter_name='Pack'+name,use_custom_primitive_data=True,
                       primitive_data_index=3+i*3,default_value=u.LinearColor(0,0,0,0))
        wire(parameter,rotated,name,'RGB')
    result=rotated
    if tangent:
        result=node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
        wire(rotated,result,str(L.get_material_expression_input_names(result)[0]))
    if not L.connect_material_property(result,'',u.MaterialProperty.MP_NORMAL):raise RuntimeError('Cannot bind sling normal')
    E.set_metadata_tag(mat,'SlingGravityNormals','R3')
if any(p.get_path_name().startswith(DEST+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Gravity-fit packages have unsaved editor edits')
E.make_directory(DEST+'/Materials')
reference=u.load_asset(OLD+'/SK_Jason_SimpleSling');mats=[]
for slot in reference.materials:
    original=slot.material_interface;path=DEST+'/Materials/'+original.get_name()
    mat=u.load_asset(path) or E.duplicate_asset(original.get_path_name().split('.')[0],path)
    if not isinstance(mat,u.Material):raise RuntimeError('Expected current editable sling motion material')
    # Large pose-relative gravity corrections are confined to the free spans.
    # Current/previous fields and the existing surface graph are preserved.
    mat.set_editor_property('max_world_position_offset_displacement',18.)
    gravity_normal(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Sling material compilation failed '+str(errors))
    L.get_statistics(mat);save(mat);mats.append(mat);saved['materials'][str(slot.material_slot_name)]=mat.get_path_name()
for row in plan['variants']:
    data=json.loads(Path(row['source']).read_text());digest=hashlib.sha256(Path(row['source']).read_bytes()).hexdigest()
    if digest!=row['sha256']:raise RuntimeError('Authoring source changed '+row['profile'])
    path=row['asset'].split('.')[0]
    mesh=u.load_asset(path) or E.duplicate_asset(reference.get_path_name().split('.')[0],path)
    native,status=G.copy_mesh_from_skeletal_mesh(reference,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read sling reference skeleton')
    dm=io.dynamic(winding.to_unreal(data),native)
    motion.apply_mask(dm,dict(positions=data['positions'],values=data['motion_mask']))
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,
        new_material_slot_names=[m['slot'] for m in data['materials']],enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save fitted sling strap')
    mesh.set_editor_property('physics_asset',None)
    mesh.set_editor_property('positive_bounds_extension',u.Vector(18,18,18));mesh.set_editor_property('negative_bounds_extension',u.Vector(18,18,18))
    E.set_metadata_tag(mesh,'SlingGravityFitRevision',plan['revision']);E.set_metadata_tag(mesh,'SourceSHA256',digest)
    save(mesh);saved['variants'][row['profile']]=dict(asset=mesh.get_path_name(),sha256=digest,saved=True,triangles=len(data['triangles']))
    receipt();print('SLING_GRAVITY_STRAP_SAVED',row['profile'],flush=True)
    del mesh,dm,native,data;gc.collect();u.SystemLibrary.collect_garbage()
saved['completed']=True;receipt();print('SLING_GRAVITY_ASSETS_COMPLETE',flush=True)
