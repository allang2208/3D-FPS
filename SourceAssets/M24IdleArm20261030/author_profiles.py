from pathlib import Path
exec(compile((Path(__file__).parent/'solve.py').read_text().split("\nif __name__=='__main__':")[0],'solver','exec'))
import copy,gzip
params=json.loads((O/'solve.json').read_text())['parameters'];roles=json.loads((O/'roles_before.json').read_text());original=copy.deepcopy(ue['profiles']);spec=copy.deepcopy(original)
reference=base['WPN_root'].inverted()@base[h]
def local_pose(clip,entry,t):
    f=min(t*clip['fps'],clip['keys']-1);i=min(int(f),clip['keys']-2);w=f-i;tracks={c['bone']:c for c in entry.get('tracks',[])};row={};locs={}
    for j,n in enumerate(names):
        a,b=unpack(clip['poses'][str(i)][j]),unpack(clip['poses'][str(i+1)][j]);p,q,sc=a[0].lerp(b[0],w),a[1].slerp(b[1],w),a[2].lerp(b[2],w)
        if n in tracks:dp,dq,ds=sample(tracks[n],t);p+=dp;q=dq@q;sc+=ds
        locs[n]=K@Matrix.LocRotScale(p,q,sc)@K;row[n]=row[parents[n]]@locs[n] if parents[n] else locs[n]
    return row,locs
def owned(n):return under(n,'clavicle_l') or n=='ik_hand_l'
report={};previews={};modified={}
for family in ('base','mag10'):
    report[family]={};modified[family]=[]
    for path,clip in roles.items():
        if 'Bipod_' in path and not path.split('.')[-1].endswith('_'+family):continue
        entry=next((c for c in original[family] if c['base']==path),{'base':path,'duration':(clip['keys']-1)/clip['fps'],'tracks':[]})
        accum={n:{'bone':n,'times':[],'values':[]} for n in names if owned(n)};weights=[];previous={};pose_rows=[]
        for i in range(clip['keys']):
            t=i/clip['fps'];row,locs=local_pose(clip,entry,t);hand=row['WPN_root'].inverted()@row[h];dist=(hand.translation-reference.translation).length;dot=abs(hand.to_quaternion().dot(reference.to_quaternion()));rot=math.degrees(2*math.acos(min(1,dot)))
            weight=(1-ease((dist-.008)/.065))*(1-ease((rot-8)/30))
            # Bipod hook, pull and release keep their recently authored contact.
            if 'Bipod_' in path:weight=1-ease(t/.12) if t<.12 else ease((t-.30)/.14) if t>.30 else 0.
            fixed=apply(row,params) if weight>1.e-6 else row;target={};local_target={}
            for n in names:
                a=locs[n];b=fixed[parents[n]].inverted()@fixed[n] if parents[n] else fixed[n]
                p,q,sc=a.decompose();pp,qq,ss=b.decompose();local_target[n]=Matrix.LocRotScale(p.lerp(pp,weight),q.slerp(qq,weight),sc.lerp(ss,weight)) if owned(n) else a
                target[n]=target[parents[n]]@local_target[n] if parents[n] else local_target[n]
                if n not in accum:continue
                # The existing profile is additive to its original base clip.
                rp,rq,rs=unpack(clip['poses'][str(i)][names.index(n)]);lp,lq,ls=(K@local_target[n]@K).decompose();dq=lq@rq.inverted()
                if n in previous and previous[n].dot(dq)<0:dq=-dq
                previous[n]=dq;accum[n]['times'].append(t);accum[n]['values'].extend([*(lp-rp),dq.x,dq.y,dq.z,dq.w,*(ls-rs)])
            weights.append(weight)
            if path.endswith('A_M24_idle') or 'Bipod_' in path:pose_rows.append({n:[list(v) for v in m] for n,m in target.items()})
        if max(weights,default=0)<1.e-6:continue
        replacement=copy.deepcopy(entry);replacement['tracks']=[tr for tr in entry['tracks'] if not owned(tr['bone'])]+list(accum.values())
        dst=next((c for c in spec[family] if c['base']==path),None)
        if dst is None:spec[family].append(replacement)
        else:dst.update(replacement)
        modified[family].append(path);report[family][path]={'keys':clip['keys'],'weights':weights}
        if pose_rows:previews[family+':'+path]={'rate':clip['fps'],'rows':pose_rows}
(O/'profile_patch.tmp.json').write_text(json.dumps({'profiles':spec,'modified':modified}));(O/'profile_patch.tmp.json').replace(O/'profile_patch.json');(O/'author_report.json').write_text(json.dumps(report))
with gzip.open(O/'preview_poses.json.gz','wt') as f:json.dump(previews,f)
# Editable idle action on the exact V9 source rig.
for family in ('base','mag10'):
    clip=ue['clips']['idle'];entry=next(c for c in spec[family] if c['base']==clip['path']);r.animation_data_clear();r.animation_data_create();action=bpy.data.actions.new('A_M24_IdleArm30_'+family);r.animation_data.action=action
    for i in range(clip['keys']):
        row,_=local_pose(clip,entry,i/clip['fps'])
        for n,m in row.items():
            loc=row[parents[n]].inverted()@m if parents[n] else m;basis=local_rest[n].inverted()@loc;p=r.pose.bones[n];p.rotation_mode='QUATERNION';p.matrix_basis=basis
            for prop in ('location','rotation_quaternion','scale'):p.keyframe_insert(prop,frame=i)
    action.use_fake_user=True
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_IdleArm_Editable.blend'))
print('IDLE_PROFILES_AUTHORED',json.dumps({k:len(v) for k,v in modified.items()}),flush=True)
