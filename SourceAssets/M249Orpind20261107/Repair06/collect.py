"""Read saved geometry and native local animation keys for the requested optic/hand review."""
from pathlib import Path
import unreal as u,pickle,json
r=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('M249 geometry unavailable')
Q,B,L=u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
_,bones=B.get_all_bones_info(dm);bones=sorted(bones,key=lambda b:b.index)
_,p,_=Q.get_all_vertex_positions(dm,False);_,f,_=Q.get_all_triangle_indices(dm,False)
vertices=[v.to_tuple() for v in L.convert_vector_list_to_array(p)]
faces=[(v.x,v.y,v.z) for v in L.convert_triangle_list_to_array(f)]
sections=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(faces))]
weights=[]
for i in range(len(vertices)):
    _,raw,valid=B.get_vertex_bone_weights(dm,i)
    if not valid:raise RuntimeError('Missing vertex weights')
    weights.append([(w.bone_index,w.weight) for w in raw if w.weight>0])
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
names=[str(b.name) for b in bones]
d=dict(vertices=vertices,faces=faces,sections=sections,weights=weights,slots=[str(s.material_slot_name) for s in mesh.materials],
       names=names,parents=[b.parent_index for b in bones],bind=[tr(b.world_transform) for b in bones])
with (r/'geometry.pkl').open('wb') as h:pickle.dump(d,h)
for role in ('idle','reload','reload_empty'):
    clip=u.load_asset('/Game/Weapons/M249/Animations/A_M249_'+role);data=clip.get_editor_property('data_model_interface')
    rate=data.get_frame_rate();fps=rate.numerator/rate.denominator;count=data.get_number_of_keys()
    frames=[]
    for frame in range(count if role!='idle' else 1):
        frames.append([tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(clip,names,frame/fps,False,mesh)])
    with (r/(role+'_local.pkl')).open('wb') as h:pickle.dump(dict(fps=fps,frames=frames),h)
    print('M249_NATIVE_POSES',role,len(frames),fps,flush=True)
report={'materials':[{'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name(),'blend':str(s.material_interface.get_base_material().get_editor_property('blend_mode'))} for s in mesh.materials],
        'morphs':[m.get_name() for m in mesh.get_editor_property('morph_targets')]}
basic=u.load_asset('/Engine/BasicShapes/BasicShapeMaterial')
report['backdrop_vector_parameters']=[str(n) for n in u.MaterialEditingLibrary.get_vector_parameter_names(basic)]
(r/'native_assets.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('M249_NATIVE_GEOMETRY',len(vertices),len(faces),flush=True)
