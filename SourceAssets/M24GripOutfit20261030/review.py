from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
from collections import Counter
patch=json.loads((O/'profile_patch.json').read_text())['profiles'];folder=O/'Review';folder.mkdir(exist_ok=True)
edges=Counter(tuple(sorted((p.vertices[i],p.vertices[(i+1)%len(p.vertices)]))) for p in skin.data.polygons for i in range(len(p.vertices)))
boundary={i for e,c in edges.items() if c==1 for i in e}
openings={side:[i for i in boundary if (skin.data.vertices[i].co-rest['upperarm_'+side].translation).length<.15] for side in ('l','r')}
report={}
path=next(p for p in roles if p.endswith('A_M24_inspect'));clip=roles[path]
for family in ('base','mag10'):
    report[family]={}
    for label,profiles in [('before',ue['profiles']),('after',patch)]:
        entry=next(c for c in profiles[family] if c['base']==path);stats={'visible_opening':{'l':0,'r':0},'wrist_max':{'l':0,'r':0},'elbow_min':{'l':180,'r':180},'elbow_max':{'l':0,'r':0},'bone_length_error_mm':0,'hand_or_weapon_shift_mm':0,'max_bone_step_degrees':0};prev=None
        original=next(c for c in ue['profiles'][family] if c['base']==path)
        for i in range(clip['keys']):
            t=i/clip['fps'];row,_=local_pose(clip,entry,t);old,_=local_pose(clip,original,t);set_pose(row)
            ev=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
            for side in ('l','r'):
                u,l,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')];U=row[l].translation-row[u].translation;L=row[h].translation-row[l].translation
                stats['wrist_max'][side]=max(stats['wrist_max'][side],angle(L,row['middle_01_'+side].translation-row[h].translation))
                b=angle(U,L);stats['elbow_min'][side]=min(stats['elbow_min'][side],b);stats['elbow_max'][side]=max(stats['elbow_max'][side],b)
                stats['bone_length_error_mm']=max(stats['bone_length_error_mm'],abs(U.length-(rest[l].translation-rest[u].translation).length)*1000,abs(L.length-(rest[h].translation-rest[l].translation).length)*1000)
                points=[C@me.vertices[k].co for k in openings[side]]
                stats['visible_opening'][side]+=sum(p.x>1 and abs(p.y)<p.x*math.tan(math.radians(37.5))*800/540 and abs(p.z)<p.x*math.tan(math.radians(37.5)) for p in points)
            ev.to_mesh_clear()
            stats['hand_or_weapon_shift_mm']=max(stats['hand_or_weapon_shift_mm'],max((row[n].translation-old[n].translation).length*1000 for n in ('hand_l','hand_r','WPN_root')))
            if prev:
                stats['max_bone_step_degrees']=max(stats['max_bone_step_degrees'],max(math.degrees(2*math.acos(min(1,abs(row[n].to_quaternion().dot(prev[n].to_quaternion()))))) for n in ('upperarm_l','lowerarm_l','upperarm_r','lowerarm_r','lowerarm_twist_01_l','lowerarm_twist_01_r')))
            prev=row
        report[family][label]=stats
        if family=='base':
            for t in (0.,.5,1.,1.5,2.,2.5,3.):
                row,_=local_pose(clip,entry,t);view(row,folder/(label+'_inspect_'+str(t)+'.png'))
(O/'targeted_review.json').write_text(json.dumps(report,indent=2));print('M24_TARGETED_REVIEW',json.dumps(report),flush=True)

# Reconstruct the registered LeaderPose followers with their actual UE bind
# matrices. This is an offline geometry review, not a runtime render assertion.
outfits={}
for name,color in [('kaitlin_skin',(.68,.52,.43,1)),('ue_field_sweater',(.13,.20,.12,1)),('ue_field_gloves_black',(.025,.03,.035,1)),('ue_st6_sleeves',(.25,.27,.18,1))]:
    data=json.loads((O/(name+'_geometry.json')).read_text());mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['positions'],[],[f['vertices'] for f in data['faces']]);mesh.update()
    ob=bpy.data.objects.new(name,mesh);s.collection.objects.link(ob);ob.color=color
    for p in mesh.polygons:p.use_smooth=True
    pts=np.asarray(data['positions']);weights={}
    for key,values in data['weights'].items():
        for bone,w in values.items():weights.setdefault(bone,np.zeros(len(pts)))[int(key)]=w
    inv={n:Matrix.LocRotScale(*unpack(v)).inverted() for n,v in data['rest'].items()};outfits[name]=(ob,pts,weights,inv)
def dress(row,shirt):
    skin.hide_render=True
    for name,(ob,pts,weights,inv) in outfits.items():
        ob.hide_render=name=='kaitlin_skin' or (name.startswith('ue_') and name not in (shirt,'ue_field_gloves_black'))
        if ob.hide_render:continue
        final=np.zeros_like(pts)
        for n,w in weights.items():
            if not np.any(w):continue
            if n not in row:raise RuntimeError('Weighted outfit bone not present in M24: '+n)
            M=np.array(row[n]@K@inv[n]);final+=(pts@M[:3,:3].T+M[:3,3])*w[:,None]
        ob.data.vertices.foreach_set('co',final.astype(np.float32).ravel());ob.data.update();ob.matrix_world=cs@C
for shirt in ('ue_field_sweater','ue_st6_sleeves'):
    for role,t in [('idle',0.),('inspect',1.)]:
        path=next(p for p in roles if p.endswith('A_M24_'+role));clip=roles[path];entry=next(c for c in patch['base'] if c['base']==path);row,_=local_pose(clip,entry,t)
        dress(row,shirt);view(row,folder/(shirt+'_'+role+'.png'))
print('M24_OUTFIT_PREVIEWS_COMPLETE',flush=True)
