from pathlib import Path
exec(compile((Path(__file__).parent/'author_profiles.py').read_text().split('report={};previews={};modified={}')[0],'author_setup','exec'))
from mathutils.bvhtree import BVHTree
patch=json.loads((O/'profile_patch.json').read_text())['profiles'];report={'bone_lengths':{},'skin':{}}
P=np.array([v.co[:] for v in skin.data.vertices]);skin.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in skin.data.loop_triangles]);_,weld=np.unique(np.round(P,6),axis=0,return_inverse=True);tw=weld[tri];nv=int(weld.max())+1
left=np.array([sum(g.weight for g in v.groups if skin.vertex_groups[g.group].name.endswith('_l'))>.5 for v in skin.data.vertices]);left_tri=left[tri].all(axis=1)
for family in ('base','mag10'):
    length_error=scale_error=0.;report['skin'][family]={}
    for entry in patch[family]:
        if entry['base'] not in roles:continue
        clip=roles[entry['base']]
        for i in range(clip['keys']):
            row,locs=local_pose(clip,entry,i/clip['fps'])
            for a,b in ((u,l),(l,h)):
                length_error=max(length_error,abs((row[b].translation-row[a].translation).length-(rest[b].translation-rest[a].translation).length))
            scale_error=max(scale_error,max((locs[n].to_scale()-Vector((1,1,1))).length for n in (u,l,h)))
    report['bone_lengths'][family]={'max_arm_length_error_mm':length_error*1000,'max_arm_scale_error':scale_error}
    for role in ('idle','aim','old_idle'):
        clip=ue['clips']['idle' if role=='old_idle' else role];entry=next(c for c in (original if role=='old_idle' else patch)[family] if c['base']==clip['path']);row,_=local_pose(clip,entry,0);set_pose(row)
        ob=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh();X=np.array([v.co[:] for v in me.vertices]);ob.to_mesh_clear();face=np.cross(X[tri[:,1]]-X[tri[:,0]],X[tri[:,2]]-X[tri[:,0]]);normals=np.zeros((nv,3))
        for j in range(3):np.add.at(normals,tw[:,j],face)
        normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12);folds=np.einsum('ij,ij->i',face,normals[tw].mean(axis=1))<0
        fold_bones={}
        for ids in tri[folds&left_tri]:
            v=skin.data.vertices[int(ids[0])];n=skin.vertex_groups[max(v.groups,key=lambda g:g.weight).group].name;fold_bones[n]=fold_bones.get(n,0)+1
        report['skin'][family][role]={'left_fold_triangles':int((folds&left_tri).sum()),'fold_bones':fold_bones,'chain':measures(row)['chain']}
(O/'review.json').write_text(json.dumps(report,indent=2));print('IDLE_REVIEW',json.dumps(report),flush=True)
