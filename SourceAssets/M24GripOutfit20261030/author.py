from pathlib import Path
exec(compile((Path(__file__).parent/'inspect_arm.py').read_text().split("\nif __name__=='__main__':")[0],'setup','exec'))
import gzip
deltas={n:Quaternion(q) for n,q in json.loads((O/'thumb_deltas.json').read_text()).items()}
deltas.update({n:Quaternion(q) for n,q in json.loads((O/'right_thumb_deltas.json').read_text()).items()})
original=copy.deepcopy(ue['profiles']);spec=copy.deepcopy(original);modified={};report={}
thumbs=set(deltas);preview={}
def held_weight(row,reference,t,path,side):
    relative=row['WPN_root'].inverted()@row['hand_'+side];dist=(relative.translation-reference.translation).length
    degrees=math.degrees(2*math.acos(min(1,abs(relative.to_quaternion().dot(reference.to_quaternion())))))
    weight=(1-ease((dist-.008)/.065))*(1-ease((degrees-8)/30))
    if 'Bipod_' in path and side=='l':weight=1-ease(t/.12) if t<.12 else ease((t-.30)/.14) if t>.30 else 0.
    if side=='r':
        n='thumb_01_r';q=(row[parents[n]].inverted()@row[n]).to_quaternion();ref=(reference_pose[parents[n]].inverted()@reference_pose[n]).to_quaternion()
        difference=math.degrees(2*math.acos(min(1,abs(q.dot(ref)))))
        weight*=1-ease((difference-5)/15)
    return weight
for family in ('base','mag10'):
    modified[family]=[];report[family]={};reference_pose=pose('idle',0,family)[0];references={side:reference_pose['WPN_root'].inverted()@reference_pose['hand_'+side] for side in ('l','r')}
    for path,clip in roles.items():
        if 'Bipod_' in path and not path.split('.')[-1].endswith('_'+family):continue
        entry=next((c for c in original[family] if c['base']==path),None)
        if entry is None:continue
        inspecting=path.endswith('A_M24_inspect');duration=(clip['keys']-1)/clip['fps']
        owned=set(thumbs)
        if inspecting:owned|={n for n in names if (under(n,'clavicle_r') or under(n,'clavicle_l'))}
        accum={n:{'bone':n,'times':[],'values':[]} for n in names if n in owned};previous={};weights=[];right_weights=[];rows=[]
        for i in range(clip['keys']):
            t=i/clip['fps'];row,locs=local_pose(clip,entry,t);grip_weights={side:held_weight(row,references[side],t,path,side) for side in ('l','r')};weights.append(max(grip_weights.values()))
            right_weights.append(grip_weights['r'])
            fixed=solve_inspect(row,t,duration) if inspecting else clone(row)
            for n in names:
                if n not in thumbs:continue
                weight=grip_weights[n[-1]]
                loc=row[parents[n]].inverted()@row[n];p,q,scale=loc.decompose()
                fixed[n]=fixed[parents[n]]@Matrix.LocRotScale(p,q.slerp(deltas[n]@q,weight),scale)
            for n,tr in accum.items():
                local=fixed[parents[n]].inverted()@fixed[n] if parents[n] else fixed[n]
                p,q,sc=(K@local@K).decompose();rp,rq,rs=unpack(clip['poses'][str(i)][names.index(n)]);dq=q@rq.inverted()
                if n in previous and previous[n].dot(dq)<0:dq=-dq
                previous[n]=dq;tr['times'].append(t);tr['values'].extend([*(p-rp),dq.x,dq.y,dq.z,dq.w,*(sc-rs)])
            if path.endswith('A_M24_idle') or inspecting:rows.append({n:[list(v) for v in m] for n,m in fixed.items()})
        if max(weights,default=0)<1e-6 and not inspecting:continue
        replacement=copy.deepcopy(entry);replacement['tracks']=[tr for tr in entry['tracks'] if tr['bone'] not in owned]+list(accum.values())
        next(c for c in spec[family] if c['base']==path).update(replacement)
        modified[family].append(path);report[family][path]={'modified_bones':len(owned),'max_grip_weight':max(weights),'keys':clip['keys'],'right_weights':right_weights}
        if rows:preview[family+':'+path]={'rate':clip['fps'],'rows':rows}
(O/'profile_patch.json').write_text(json.dumps({'profiles':spec,'modified':modified}));(O/'author_report.json').write_text(json.dumps(report,indent=2))
with gzip.open(O/'preview_poses.json.gz','wt') as f:json.dump(preview,f)
for family in ('base','mag10'):
    for role in ('idle','inspect'):
        path=next(p for p in roles if p.endswith('A_M24_'+role));clip=roles[path];entry=next(c for c in spec[family] if c['base']==path)
        r.animation_data_clear();r.animation_data_create();action=bpy.data.actions.new('A_M24_GripOutfit30_'+family+'_'+role);r.animation_data.action=action
        for i in range(clip['keys']):
            row,_=local_pose(clip,entry,i/clip['fps'])
            for n,m in row.items():
                loc=row[parents[n]].inverted()@m if parents[n] else m;p=r.pose.bones[n];p.rotation_mode='QUATERNION';p.matrix_basis=local_rest[n].inverted()@loc
                for prop in ('location','rotation_quaternion','scale'):p.keyframe_insert(prop,frame=i)
        action.use_fake_user=True
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_GripOutfit_Editable.blend'))
print('M24_GRIP_INSPECT_AUTHORED',json.dumps({k:len(v) for k,v in modified.items()}),flush=True)
