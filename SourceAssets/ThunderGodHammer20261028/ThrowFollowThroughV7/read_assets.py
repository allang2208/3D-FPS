"""Read only: current shipped arm surface and sequence data-model poses."""
import unreal as u,json,hashlib,math
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
path='/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1'
mesh=u.load_asset(path);Q=u.GeometryScript_MeshQueries;BW=u.GeometryScript_BoneWeights
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native mesh read failed')
_,positions,_=Q.get_all_vertex_positions(dm,False);positions=u.GeometryScript_List.convert_vector_list_to_array(positions)
_,triangles,_=Q.get_all_triangle_indices(dm,False);triangles=u.GeometryScript_List.convert_triangle_list_to_array(triangles)
_,info=BW.get_all_bones_info(dm);info=sorted(info,key=lambda b:b.index);names=[str(b.name) for b in info];byid={b.index:str(b.name) for b in info}
def xyz(v):return [v.x,v.y,v.z]
def tr(t):return xyz(t.translation)+[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]+xyz(t.scale3d)
bones={str(b.name):{'parent':byid.get(b.parent_index),'transform':tr(b.world_transform)} for b in info}
weights=[]
for i in range(len(positions)):
    _,w,ok=BW.get_vertex_bone_weights(dm,i)
    weights.append({byid[a.bone_index]:a.weight for a in w if a.weight>0} if ok else {})
slots=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else ''} for s in mesh.materials]
data={'mesh':path,'positions':[xyz(v) for v in positions],'triangles':[list(map(int,xyz(v))) for v in triangles],
      'bones':bones,'weights':weights,'slots':slots,'morph_names':[m.get_name() for m in mesh.get_editor_property('morph_targets')],
      'mesh_sha256':hashlib.sha256((R/'Content'/ (path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()}
(P/'native-mesh.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
poses={};meta={}
for short in ('Charge','Release'):
    name='A_ThunderHammer_Throw'+short;asset='/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1/'+name
    seq=u.load_asset(asset);model=seq.get_editor_property('data_model_interface');rate=model.get_frame_rate();fps=rate.numerator/rate.denominator;n=model.get_number_of_keys()
    frames=[]
    for i in range(n):
        local=dict(zip(names,u.AnimationLibrary.get_bone_poses_for_time(seq,names,i/fps,False,mesh)));comp={}
        for b in names:
            parent=bones[b]['parent'];comp[b]=local[b].multiply(comp[parent]) if parent else local[b]
        frames.append([tr(comp[b]) for b in names])
    poses[short]={'names':names,'fps':fps,'frames':frames}
    meta[short]={'asset':asset,'fps':fps,'keys':n,'length':(n-1)/fps,'same_skeleton':seq.get_editor_property('skeleton')==mesh.get_editor_property('skeleton'),
                 'revision':u.EditorAssetLibrary.get_metadata_tag(seq,'ThunderThrowRevision')}
(P/'native-poses.json').write_text(json.dumps(poses,separators=(',',':')),encoding='utf-8')
(P/'native-read-receipt.json').write_text(json.dumps({'mesh':path,'vertices':len(positions),'triangles':len(triangles),'poses':meta,'reader':'sequence_data_model_by_time','read_only':True},indent=2),encoding='utf-8')
print('THUNDER_NATIVE_THROW_READ '+json.dumps(meta),flush=True)
