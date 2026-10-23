"""Save isolated fitted/sway variants, retaining approved source meshes and LODs."""
import json,hashlib,importlib.util,math,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackMotion20261022';DEST='/Game/Characters/BackpackMotion20261022'
E,G,L=u.EditorAssetLibrary,u.GeometryScript_AssetUtils,u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
plan=json.loads((R/'manifest.json').read_text())
saved=json.loads((R/'saved_assets.json').read_text()) if (R/'saved_assets.json').exists() else {'variants':{},'materials':{}}
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('motion_dynamic_io',P/'Tools/ChainmailPants/save_assets.py');winding=module('motion_winding',P/'Tools/BackpackHarness/winding.py')
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside isolated motion asset scope')
    asset.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):
        raise RuntimeError('Asset was not saved '+asset.get_path_name())
def receipt():
    saved.update(revision=plan['revision'],runtime_tested=False)
    (R/'saved_assets.json').write_text(json.dumps(saved,indent=2))
def node(mat,kind,**properties):
    n=L.create_material_expression(mat,kind)
    for key,value in properties.items():n.set_editor_property(key,value)
    return n
def wire(a,b,pin,output=''):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect motion material '+pin)
def motion_material(original):
    source=original.get_path_name();name='M_Motion_'+original.get_name()+'_'+hashlib.sha1(source.encode()).hexdigest()[:6]
    path=DEST+'/Materials/'+name
    mat=u.load_asset(path)
    if mat and E.get_metadata_tag(mat,'BackpackMotionRevision')==plan['revision']:return mat
    if not mat:mat=E.duplicate_asset(source.split('.')[0],path)
    if not isinstance(mat,u.Material):raise RuntimeError('Expected an editable backpack base material '+source)
    if mat.get_editor_property('use_material_attributes'):raise RuntimeError('Source requires an attributes-preserving WPO insertion '+source)
    position=node(mat,u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    mask=node(mat,u.MaterialExpressionVertexColor)
    def field(previous):
        offset=15 if previous else 0
        names=['Pivot','RowX','RowY','RowZ','Shift'];nodes=[]
        for index,name in enumerate(names):
            nodes.append(node(mat,u.MaterialExpressionVectorParameter,parameter_name='Pack'+('Previous' if previous else '')+name,
                              default_value=u.LinearColor(0,0,0,0),use_custom_primitive_data=True,primitive_data_index=offset+index*3))
        custom=node(mat,u.MaterialExpressionCustom,description='Backpack pinned inertia',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
                    code='float3 q=Position-Pivot; return (float3(dot(RowX,q),dot(RowY,q),dot(RowZ,q))+Shift)*saturate(Mask);')
        inputs=[]
        for name in ['Position',*names,'Mask']:
            entry=u.CustomInput();entry.set_editor_property('input_name',name);inputs.append(entry)
        custom.set_editor_property('inputs',inputs)
        wire(position,custom,'Position')
        for name,n in zip(names,nodes):wire(n,custom,name,'RGB')
        wire(mask,custom,'Mask','R');return custom
    switch=node(mat,u.MaterialExpressionPreviousFrameSwitch)
    wire(field(False),switch,'Current Frame');wire(field(True),switch,'Previous Frame')
    if not L.connect_material_property(switch,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET):raise RuntimeError('Cannot bind pack deformation')
    mat.set_editor_property('max_world_position_offset_displacement',6.)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Backpack material compilation failed '+str(errors))
    E.set_metadata_tag(mat,'BackpackMotionRevision',plan['revision']);save(mat)
    saved['materials'][source]=mat.get_path_name();receipt();return mat

def apply_mask(dm,maskdata):
    # Exact authored stations match LOD0 and the retained harness in LOD1.
    # Other LOD1 vertices belong to the reduced rigid bag and remain weight 1.
    lookup={tuple(round(c,3) for c in p):v for p,v in zip(maskdata['positions'],maskdata['values'])}
    buckets={}
    for p,value in zip(maskdata['positions'],maskdata['values']):
        if value<1.:buckets.setdefault(tuple(math.floor(c*4) for c in p),[]).append((p,value))
    def weight(p):
        point=[p.x,p.y,p.z];value=lookup.get(tuple(round(c,3) for c in point))
        if value is not None:return value
        cell=tuple(math.floor(c*4) for c in point);best=.02**2;result=1.
        for x in [-1,0,1]:
            for y in [-1,0,1]:
                for z in [-1,0,1]:
                    for source,value in buckets.get((cell[0]+x,cell[1]+y,cell[2]+z),[]):
                        distance=sum((a-b)**2 for a,b in zip(point,source))
                        if distance<best:best=distance;result=value
        return result
    _,points,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
    colors=[u.LinearColor(weight(p),0,0,1)
            for p in u.GeometryScript_List.convert_vector_list_to_array(points)]
    color_list=u.GeometryScript_List.convert_array_to_color_list(colors)
    u.GeometryScript_VertexColors.set_mesh_per_vertex_colors(dm,color_list)

def apply_fit_delta(dm,path):
    fit=json.loads(Path(path).read_text())
    lookup={tuple(round(c,3) for c in p):delta for p,delta in zip(fit['before'],fit['delta'])}
    buckets={}
    for p,delta in zip(fit['before'],fit['delta']):
        buckets.setdefault(tuple(math.floor(c*4) for c in p),[]).append((p,delta))
    _,points,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
    _,triangles,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)
    points=u.GeometryScript_List.convert_vector_list_to_array(points)
    triangles=u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    harness=set()
    for i,t in enumerate(triangles):
        if u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0]!=0:harness.update([t.x,t.y,t.z])
    values=[];unmatched_bag=0
    for i,p in enumerate(points):
        delta=lookup.get(tuple(round(c,3) for c in [p.x,p.y,p.z]))
        if delta is None and i in harness:
            point=[p.x,p.y,p.z];cell=tuple(math.floor(c*4) for c in point);best=.02**2
            for x in [-1,0,1]:
                for y in [-1,0,1]:
                    for z in [-1,0,1]:
                        for candidate,change in buckets.get((cell[0]+x,cell[1]+y,cell[2]+z),[]):
                            distance=sum((a-b)**2 for a,b in zip(candidate,point))
                            if distance<best:best=distance;delta=change
        if delta is None:
            if i in harness:raise RuntimeError('Refit cannot identify retained LOD harness vertex '+str(i))
            delta=[0,-fit['bag_rear_cm'],0];unmatched_bag+=1
        values.append(u.Vector(p.x+delta[0],p.y+delta[1],p.z+delta[2]))
    u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,u.GeometryScript_List.convert_array_to_vector_list(values))
    # Existing normal overlays retain their hard-edge splits and UE winding.
    u.GeometryScript_Normals.recompute_normals(dm,u.GeometryScriptCalculateNormalsOptions())
    print('BACKPACK_REFIT_LOD',len(points),'reduced_bag_vertices',unmatched_bag,flush=True)

def main():
    for row in plan['variants']:
        if hashlib.sha256(Path(row['source']).read_bytes()).hexdigest()!=row['source_sha256'] or hashlib.sha256(Path(row['mask']).read_bytes()).hexdigest()!=row.get('mask_sha256'):
            raise RuntimeError('Finish source and seam-mask preparation before saving '+row['kind']+'/'+row['profile'])
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('Finish PIE before saving fitted backpacks')
        if any(p.get_path_name().startswith(DEST+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Motion assets have unsaved editor edits')
    E.make_directory(DEST+'/Materials')
    for row in plan['variants']:
        key=row['kind']+'/'+row['profile'];src=Path(row['source']);digest=hashlib.sha256(src.read_bytes()+Path(row['mask']).read_bytes()).hexdigest()
        if hashlib.sha256(src.read_bytes()).hexdigest()!=row['source_sha256'] or hashlib.sha256(Path(row['mask']).read_bytes()).hexdigest()!=row['mask_sha256']:
            raise RuntimeError('Authored source changed during import '+key)
        path=row['asset'].split('.')[0]
        if saved['variants'].get(key,{}).get('sha256')==digest and E.does_asset_exist(path):
            print('BACKPACK_MOTION_RESUME',key,flush=True);continue
        source=u.load_asset(row['input_asset']);mesh=u.load_asset(path) or E.duplicate_asset(row['input_asset'].split('.')[0],path)
        if not source or not mesh:raise RuntimeError('Missing backpack source '+key)
        data=json.loads(src.read_text());maskdata=json.loads(Path(row['mask']).read_text())
        materials=[motion_material(u.load_asset(m['asset'])) for m in data['materials']]
        lod_count=1 if row['new_geometry'] else S.get_lod_count(source)
        if row['new_geometry'] and S.get_lod_count(mesh)>1:S.remove_lods(mesh,list(range(1,S.get_lod_count(mesh))))
        counts=[]
        for lod in range(lod_count):
            native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_index=lod))
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native backpack LOD')
            dm=io.dynamic(winding.to_unreal(data),native) if row['new_geometry'] else native
            if row.get('fit_delta'):apply_fit_delta(dm,row['fit_delta'])
            apply_mask(dm,maskdata)
            options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,new_material_slot_names=[m['slot'] for m in data['materials']],
                enable_recompute_normals=False,enable_recompute_tangents=True,
                bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
            _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD(lod_index=lod))
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write backpack motion LOD')
            setting=S.get_lod_build_settings(mesh,lod);setting.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(mesh,lod,setting)
            counts.append(dm.get_triangle_count());del dm,native
        mesh.set_editor_property('physics_asset',None)
        mesh.set_editor_property('positive_bounds_extension',u.Vector(6,6,6));mesh.set_editor_property('negative_bounds_extension',u.Vector(6,6,6))
        E.set_metadata_tag(mesh,'BackpackMotionRevision',plan['revision']);E.set_metadata_tag(mesh,'BackpackFrontFaceConvention',winding.UE_CONVENTION)
        save(mesh)
        saved['variants'][key]={'asset':mesh.get_path_name(),'sha256':digest,'saved':True,'lod_triangles':counts,'materials':[m.get_path_name() for m in materials]};receipt()
        print('BACKPACK_MOTION_SAVED',key,flush=True)
        del mesh,source,data,maskdata;gc.collect();u.SystemLibrary.collect_garbage()
    saved['completed']=True;receipt();print('BACKPACK_MOTION_ASSETS_COMPLETE',flush=True)
if __name__=='__main__':main()
