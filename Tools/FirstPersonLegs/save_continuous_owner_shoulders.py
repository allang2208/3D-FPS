"""Split the owner torso/sleeve seam inside triangles instead of hiding whole faces.

Runs offline on saved source assets. Never reads a live skeletal component.
"""
import json, math
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SleeveSpikeRepair20261006'
DEST='/Game/Characters/ModularOutfit20260924/OwnerShoulderSeam20261006'
C=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
M=u.GeometryScript_Materials;L=u.GeometryScript_List;E=u.GeometryScript_MeshEdits
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
THRESHOLD=.4
R.mkdir(parents=True,exist_ok=True)
receipt=R/'saved_shoulders.json'
saved=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else {}

def preserve_shoulder_lods(asset,name):
    if not u.FPSModularOutfitComponent.configure_outfit_lods(asset):raise RuntimeError('Cannot configure owner LODs')
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
    policy=u.AssetToolsHelpers.get_asset_tools().create_asset(name+'_LODPolicy',DEST,u.SkeletalMeshLODSettings,factory)
    if not policy:raise RuntimeError('Cannot create owner shoulder LOD policy')
    lods=[]
    for index in range(3):
        info=u.SkeletalMeshLODGroupSettings();settings=info.get_editor_property('reduction_settings')
        settings.set_editor_property('num_of_triangles_percentage',1.)
        settings.set_editor_property('max_bones_per_vertex',8)
        settings.set_editor_property('lock_edges',True)
        settings.set_editor_property('enforce_bone_boundaries',True)
        settings.set_editor_property('merge_coincident_vert_bones',False)
        settings.set_editor_property('welding_threshold',0.)
        settings.set_editor_property('recalc_normals',False)
        info.set_editor_property('reduction_settings',settings)
        info.set_editor_property('screen_size',u.PerPlatformFloat(default=[1.,.18,.075][index]));lods.append(info)
    policy.set_editor_property('lod_groups',lods)
    asset.set_editor_property('lod_settings',policy)
    models=list(asset.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',lods[i].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models',models)
    build=S.get_lod_build_settings(asset,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,build)
    if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('Cannot generate owner LODs')
    return policy

def clip(poly,inside):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ia=inside(a[1]);ib=inside(b[1])
        if ia:result.append(a)
        if ia!=ib:
            t=(THRESHOLD-a[1])/(b[1]-a[1])
            result.append(([a[0][i]+t*(b[0][i]-a[0][i]) for i in range(3)],THRESHOLD))
    return result

for item in ['ue_field_sweater','ue_field_sweater_charcoal','ue_chainmail_shirt']:
    path=C['items'][item]['rig_meshes']['Jason']
    if item in saved:
        if saved[item]['source']!=path:raise RuntimeError('Source changed after partial save: '+item)
        print('CONTINUOUS_OWNER_SHOULDER_ALREADY_SAVED '+item,flush=True);continue
    name='SK_Jason_Owner_'+item
    if u.EditorAssetLibrary.does_asset_exist(DEST+'/'+name):raise RuntimeError('Unrecorded destination already exists: '+name)
    source=u.load_asset(path)
    if not source:raise RuntimeError('Missing world shirt '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read source '+path)
    _,bones=B.get_all_bones_info(dm);by_id={b.index:b for b in bones};arm_ids=set()
    for bone in bones:
        index=bone.index
        while index>=0:
            parent=by_id[index]
            if str(parent.name) in ['upperarm_l','upperarm_r']:
                arm_ids.add(bone.index);break
            index=parent.parent_index
    _,ps,_=Q.get_all_vertex_positions(dm,False);positions=L.convert_vector_list_to_array(ps)
    _,ts,_=Q.get_all_triangle_indices(dm,False);triangles=L.convert_triangle_list_to_array(ts)
    weights=[];arm=[]
    for vi in range(len(positions)):
        _,ws,valid=B.get_vertex_bone_weights(dm,vi)
        if not valid:raise RuntimeError('Missing native weights')
        weights.append({w.bone_index:w.weight for w in ws})
        arm.append(sum(w.weight for w in ws if w.bone_index in arm_ids))
    slots=list(source.materials);n=len(slots);uv_count=Q.get_num_uv_sets(dm)
    # Native vertices, UV seams and every uncut face remain in the source mesh.
    # Only mixed shoulder faces are replaced with interpolated sub-triangles.
    pending=[];crossed=[]
    for ti,t in enumerate(triangles):
        ids=[t.x,t.y,t.z];values=[arm[v] for v in ids];mat=M.get_triangle_material_id(dm,ti)[0]
        if min(values)>=THRESHOLD:
            M.set_triangle_material_id(dm,ti,mat+n,True);continue
        if max(values)<=THRESHOLD:continue
        _,*ns=Q.get_triangle_normals(dm,ti)
        if not ns[3]:raise RuntimeError('Missing shoulder normals')
        uvs=[]
        for channel in range(min(uv_count,8)):
            uv=Q.get_triangle_u_vs(dm,channel,ti)
            if not uv[3]:raise RuntimeError('Missing shoulder UV channel')
            uvs.append(uv[:3])
        if not uvs:raise RuntimeError('Missing shoulder UVs')
        poly=[([float(i==j) for i in range(3)],values[j]) for j in range(3)]
        for hidden,inside in [(False,lambda x:x<=THRESHOLD),(True,lambda x:x>=THRESHOLD)]:
            part=clip(poly,inside)
            for i in range(1,len(part)-1):
                bary=[part[0][0],part[i][0],part[i+1][0]]
                if any(sum(abs(bary[a][j]-bary[b][j]) for j in range(3))<1e-8 for a,b in [(0,1),(1,2),(2,0)]):continue
                verts=[];normals=[];out_uvs=[[] for _ in uvs];out_weights=[]
                for b in bary:
                    verts.append(sum((positions[ids[j]]*b[j] for j in range(3)),u.Vector()))
                    normal=sum((ns[j]*b[j] for j in range(3)),u.Vector())
                    length=math.sqrt(normal.x*normal.x+normal.y*normal.y+normal.z*normal.z)
                    normal=normal*(1./max(length,1e-12))
                    normals.append(normal)
                    for ci,uv in enumerate(uvs):out_uvs[ci].append(sum((uv[j]*b[j] for j in range(3)),u.Vector2D()))
                    ws={}
                    for j in range(3):
                        for bone,weight in weights[ids[j]].items():ws[bone]=ws.get(bone,0.)+b[j]*weight
                    ordered=sorted(((bone,w) for bone,w in ws.items() if w>1e-8),key=lambda x:x[1],reverse=True)[:8]
                    total=sum(w for _,w in ordered)
                    out_weights.append([u.GeometryScriptBoneWeight(bone_index=bone,weight=w/total) for bone,w in ordered])
                pending.append((verts,normals,out_uvs,out_weights,mat+(n if hidden else 0)))
        crossed.append(ti)
    # Append before deleting source faces; use returned triangle IDs rather than
    # assuming dynamic-mesh vertex IDs are compact or sequential.
    for verts,normals,uvs,ws,material in pending:
        buffer=u.GeometryScriptSimpleMeshBuffers(vertices=verts,normals=normals,triangles=[u.IntVector(0,1,2)])
        for channel,uv in enumerate(uvs):buffer.set_editor_property('uv'+str(channel),uv)
        _,new_list=E.append_buffers_to_mesh(dm,buffer,material,True)
        new_ids=L.convert_index_list_to_array(new_list)
        if len(new_ids)!=1:raise RuntimeError('Cannot split shoulder face')
        indices,valid=Q.get_triangle_indices(dm,new_ids[0])
        if not valid:raise RuntimeError('Missing appended shoulder face')
        for vi,weight in zip([indices.x,indices.y,indices.z],ws):
            _,valid=B.set_vertex_bone_weights(dm,vi,weight)
            if not valid:raise RuntimeError('Cannot bind new shoulder vertex')
    for ti in crossed:
        _,deleted=E.delete_triangle_from_mesh(dm,ti,True)
        if not deleted:raise RuntimeError('Cannot replace shoulder face')
    asset=u.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,DEST,source)
    if not asset:raise RuntimeError('Destination exists or cannot be created: '+name)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots]*2,
        new_material_slot_names=[str(s.material_slot_name) for s in slots]+['OwnerHiddenArms_'+str(s.material_slot_name) for s in slots],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save continuous shoulder geometry')
    # Keep the new paired seam topology at each owner-body LOD. Independent
    # reduction of coincident inner/outer shoulder edges would reopen that seam.
    policy=preserve_shoulder_lods(asset,name)
    asset.set_editor_property('physics_asset',None)
    u.EditorAssetLibrary.set_metadata_tag(asset,'OwnerBodySource',path)
    u.EditorAssetLibrary.set_metadata_tag(asset,'OwnerBodyMethod','Continuous arm-weight shoulder seam; original native binding')
    asset.modify()
    if not u.EditorLoadingAndSavingUtils.save_packages([policy.get_outer(),asset.get_outer()],False):raise RuntimeError('Package not saved')
    saved[item]=dict(source=path,mesh=asset.get_path_name(),hidden_materials=list(range(n,2*n)),split_source_triangles=len(crossed),replacement_triangles=len(pending))
    receipt.write_text(json.dumps(saved,indent=2),encoding='utf-8')
    print('CONTINUOUS_OWNER_SHOULDER_SAVED '+item,flush=True)
print('CONTINUOUS_OWNER_SHOULDERS_COMPLETE',flush=True)
