"""Save the full display, shared Nanite body and six fitted harnesses."""
import json,hashlib,importlib.util,gc
from array import array
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/PathfinderBackpack20261023';DEST='/Game/Characters/PathfinderBackpack20261023'
OLD='/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003'
E,G,L=u.EditorAssetLibrary,u.GeometryScript_AssetUtils,u.MaterialEditingLibrary
A=u.AssetToolsHelpers.get_asset_tools();S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
compiled_materials=set()
plan=json.loads((R/'manifest.json').read_text());saved=json.loads((R/'saved_assets.json').read_text()) if (R/'saved_assets.json').exists() else {'variants':{},'materials':{}}
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('sling_io',P/'Tools/ChainmailPants/save_assets.py');winding=module('sling_winding',P/'Tools/BackpackHarness/winding.py')
motion=module('sling_motion',P/'Tools/BackpackMotion/save_assets.py')
# Reuse the existing deformation graph only; all writes belong to this new item.
motion.R=R;motion.DEST=DEST;motion.plan=plan;motion.saved=saved
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside sling asset scope')
    asset.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):
        raise RuntimeError('Cannot save '+asset.get_path_name())
def receipt():
    saved.update(revision=plan['revision'],runtime_tested=False,accepted_by_user=False)
    (R/'saved_assets.json').write_text(json.dumps(saved,indent=2))
def compile_save(mat):
    if mat.get_path_name() in compiled_materials:return
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Material compile failed '+str(errors))
    stats=L.get_statistics(mat)
    if stats.num_vertex_shader_instructions<=0 or stats.num_pixel_shader_instructions<=0:raise RuntimeError('Real RHI material compilation required')
    save(mat);compiled_materials.add(mat.get_path_name())
    saved.setdefault('shader_compilation',{})[mat.get_path_name()]={'vertex_instructions':stats.num_vertex_shader_instructions,'pixel_instructions':stats.num_pixel_shader_instructions}
def material(name):
    mat=u.load_asset(DEST+'/'+name) or A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    for expression in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,expression)
    return mat
def output(node,pin,prop):
    if not L.connect_material_property(node,pin,prop):raise RuntimeError('Cannot connect material property')
def materials():
    textures={};E.make_directory(DEST+'/Textures')
    for channel,name in [('BaseColor','T_Pathfinder_BaseColor'),('MR','T_Pathfinder_MetallicRoughness'),('Normal','T_Pathfinder_Normal_GL')]:
        task=u.AssetImportTask();task.filename=str(R/'Textures'/(name+'.png'));task.destination_path=DEST+'/Textures';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(task.destination_path+'/'+name)
        if not tex:raise RuntimeError('Texture import failed '+name)
        tex.set_editor_property('srgb',channel=='BaseColor');tex.set_editor_property('never_stream',False)
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='MR' else u.TextureCompressionSettings.TC_DEFAULT)
        if channel=='Normal':tex.set_editor_property('flip_green_channel',True)
        save(tex);textures[channel]=tex
    mat=material('M_PathfinderBackpack');mat.set_editor_property('two_sided',True)
    for channel,tex in textures.items():
        node=L.create_material_expression(mat,u.MaterialExpressionTextureSample);node.set_editor_property('texture',tex)
        node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='MR' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        if channel=='BaseColor':output(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        elif channel=='Normal':output(node,'RGB',u.MaterialProperty.MP_NORMAL)
        else:output(node,'G',u.MaterialProperty.MP_ROUGHNESS);output(node,'B',u.MaterialProperty.MP_METALLIC)
    compile_save(mat)
    for src,name in [('/Game/Characters/ExpeditionBackpack20261022/M_ExpeditionHarness_Fabric','M_PathfinderHarness_Fabric'),(OLD+'/M_BackpackHarness_Hardware','M_PathfinderHarness_Hardware')]:
        target=u.load_asset(DEST+'/'+name) or E.duplicate_asset(src,DEST+'/'+name)
        if not target:raise RuntimeError('Missing fitted harness material')
        if name.endswith('Fabric'):
            # Keep the proven woven PBR graph; tint the actual cloth, never its
            # deformation mask. This backpack uses a darker technical webbing.
            for expression in L.get_material_expressions(target):
                if isinstance(expression,u.MaterialExpressionConstant3Vector):expression.set_editor_property('constant',u.LinearColor(.38,.40,.32,1))
        L.set_material_usage(target,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);compile_save(target)

    receipt()
def read_array(folder,name,kind):
    result=array(kind);result.frombytes((folder/(name+'.bin')).read_bytes());return result
def vectors(values,count,ctor):
    it=iter(values);return [ctor(*row) for row in zip(*[it]*count)]
def static(kind,name):
    folder=R/'Authored'/kind;metadata=json.loads((folder/'buffers.json').read_text())
    digest=hashlib.sha256(b''.join((folder/(n+'.bin')).read_bytes() for n in ['positions','normals','uv','triangles','materials'])).hexdigest()
    path=DEST+'/'+name
    if saved.get(kind,{}).get('sha256')==digest and E.does_asset_exist(path):return
    vertices=vectors(read_array(folder,'positions','f'),3,u.Vector);normals=vectors(read_array(folder,'normals','f'),3,u.Vector)
    uv=vectors(read_array(folder,'uv','f'),2,u.Vector2D);it=iter(read_array(folder,'triangles','i'))
    triangles=[u.IntVector(a,c,b) for a,b,c in zip(it,it,it)]
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv,triangles=triangles),0,True)
    for ti,slot in enumerate(read_array(folder,'materials','i')):
        if slot:u.GeometryScript_Materials.set_triangle_material_id(dm,ti,slot,True)
    del vertices,normals,uv,triangles;gc.collect()
    mesh=u.load_asset(path)
    if mesh:_,status=G.copy_mesh_to_static_mesh(dm,mesh,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
    else:mesh,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_collision=False,enable_nanite=True))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot create static sling '+kind)
    mats=[u.load_asset(DEST+'/M_PathfinderBackpack')]
    mesh.set_editor_property('static_materials',[u.StaticMaterial(material_interface=m,material_slot_name='Sling_'+str(i)) for i,m in enumerate(mats)])
    E.set_metadata_tag(mesh,'SourceSHA256',digest);E.set_metadata_tag(mesh,'BackpackFrontFaceConvention',winding.UE_CONVENTION);save(mesh)
    saved[kind]={'asset':mesh.get_path_name(),'sha256':digest,'saved':True,'triangles':metadata['triangles'],'nanite':True};receipt()
    del dm,mesh;gc.collect();u.SystemLibrary.collect_garbage();print('PATHFINDER_STATIC_SAVED',kind,flush=True)
def wearable(row):
    profile=row['profile'];src=Path(row['source']);digest=hashlib.sha256(src.read_bytes()).hexdigest();path=row['asset'].split('.')[0]
    if saved['variants'].get(profile,{}).get('sha256')==digest and E.does_asset_exist(path):return
    data=json.loads(src.read_text());mesh=u.load_asset(path) or E.duplicate_asset(OLD+'/SK_Jason_Backpack',path)
    if not mesh:raise RuntimeError('Cannot create sling variant '+profile)
    native,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot load reference bones')
    count=S.get_lod_count(mesh)
    if count>1 and not S.remove_lods(mesh,list(range(1,count))):raise RuntimeError('Cannot remove inherited backpack LODs')
    dm=io.dynamic(winding.to_unreal(data),native);motion.apply_mask(dm,{'positions':data['positions'],'values':data['motion_mask']})
    mats=[motion.motion_material(u.load_asset(m['asset'])) for m in data['materials']]
    for mat in mats:compile_save(mat)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=[m['slot'] for m in data['materials']],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD(lod_index=0))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save sling strap '+profile)
    setting=S.get_lod_build_settings(mesh,0);setting.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(mesh,0,setting)
    mesh.set_editor_property('physics_asset',None);mesh.set_editor_property('positive_bounds_extension',u.Vector(6,6,6));mesh.set_editor_property('negative_bounds_extension',u.Vector(6,6,6))
    E.set_metadata_tag(mesh,'EquipmentDefinition','ue_pathfinder_backpack');E.set_metadata_tag(mesh,'BackpackFrontFaceConvention',winding.UE_CONVENTION);E.set_metadata_tag(mesh,'SourceSHA256',digest);save(mesh)
    saved['variants'][profile]={'asset':mesh.get_path_name(),'sha256':digest,'saved':True,'triangles':len(data['triangles']),'lod_count':1};receipt()
    del dm,native,data,mesh;gc.collect();u.SystemLibrary.collect_garbage();print('PATHFINDER_WEARABLE_SAVED',profile,flush=True)
def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('Finish PIE before authoring assets')
        if any(p.get_path_name().startswith(DEST+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Sling assets have unsaved editor edits')
    E.make_directory(DEST);materials();static('Display','SM_PathfinderBackpack');static('Worn','SM_PathfinderWornBody')
    for row in plan['variants']:wearable(row)
    saved['completed']=True;receipt();print('PATHFINDER_ASSETS_COMPLETE',flush=True)
if __name__=='__main__':
    status=R/'asset_job_status.json';status.write_text(json.dumps({'state':'running'}))
    try:
        main();status.write_text(json.dumps({'state':'completed'}))
    except Exception as error:
        import traceback
        status.write_text(json.dumps({'state':'failed','error':str(error),'traceback':traceback.format_exc()},indent=2));raise
