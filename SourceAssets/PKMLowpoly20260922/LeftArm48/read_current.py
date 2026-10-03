"""Read the actual PKM native arm surface and installed animation tracks for repair."""
import json
from pathlib import Path
import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
config = json.loads((PROJECT/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
path, profile = next((p, v) for p, v in config['profiles'].items() if v['rig_profile'] == 'PKM')
mesh = u.load_asset(path)
Q, B, G = u.GeometryScript_MeshQueries, u.GeometryScript_BoneWeights, u.GeometryScript_AssetUtils
def xyz(v): return [v.x, v.y, v.z]
def packed(t):
    return {'position': xyz(t.translation), 'axes': [xyz(t.transform_location(v)-t.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]}

dm, status = G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot extract PKM')
_, bones = B.get_all_bones_info(dm)
names = {b.index: str(b.name) for b in bones}
_, p, _ = Q.get_all_vertex_positions(dm,False)
positions = u.GeometryScript_List.convert_vector_list_to_array(p)
_, t, _ = Q.get_all_triangle_indices(dm,False)
triangles = u.GeometryScript_List.convert_triangle_list_to_array(t)
faces=[]; normals=[]; mats=[]
for i, t in enumerate(triangles):
    mat, valid = u.GeometryScript_Materials.get_triangle_material_id(dm,i)
    if not valid or mat not in profile['hide_source_materials']: continue
    _, a,b,c,valid = Q.get_triangle_normals(dm,i)
    faces.append(xyz(t)); normals.append([xyz(v) for v in (a,b,c)]); mats.append(mat)
ids = sorted({i for t in faces for i in t}); index={v:i for i,v in enumerate(ids)}
weights=[]
for i in ids:
    _, ws, valid = B.get_vertex_bone_weights(dm,i)
    weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
data={'source':path,'profile':profile,'positions':[xyz(positions[i]) for i in ids], 'weights':weights,
      'triangles':[[index[i] for i in t] for t in faces], 'normals':normals,'triangle_materials':mats,
      'bones':{str(b.name):dict(packed(b.world_transform),parent=b.parent_index,index=b.index) for b in bones}}
(HERE/'current_mesh.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')

base='/Game/Weapons/PKMLowpoly20260922'
assets=[base+'/Animations/A_PKM_'+s for s in ['idle','reload','reload_empty','equip','sprint_enter','sprint_loop','sprint_exit']]
assets += [base+'/Accessories14/Animations/'+f+'/A_PKM_'+f+'_'+s for f in ['angled','canted','prism','vertical'] for s in ['idle','reload','reload_empty']]
armnames=[n for n in names.values() if n.endswith('_l') and any(k in n for k in ['clavicle','upperarm','lowerarm','hand'])]
all_data={}
for path in assets:
    anim=u.load_asset(path)
    if not anim: raise RuntimeError(path)
    opt=u.AnimPoseEvaluationOptions(); opt.optional_skeletal_mesh=mesh; opt.evaluation_type=u.AnimDataEvalType.RAW
    length=anim.get_play_length()
    times=[0.] if path.endswith('idle') else [length*i/32 for i in range(33)]
    frames=[]
    for at in times:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,at,opt)
        frames.append({n:packed(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in armnames})
    opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,0,opt)
    all_data[path]={'source':anim.get_editor_property('asset_import_data').get_first_filename(),'length':length,
       'times':times,'frames':frames,'compressed_start':{n:packed(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in armnames}}
(HERE/'current_poses.json').write_text(json.dumps(all_data,separators=(',',':')),encoding='utf-8')
print('PKM_LEFT_ARM_INPUTS',len(ids),len(faces),len(assets))
