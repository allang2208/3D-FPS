from pathlib import Path
exec(compile((Path(__file__).parent/'solve.py').read_text().split("\nif __name__=='__main__':")[0],'solver','exec'))
original=copy.deepcopy(ue['profiles']);spec=copy.deepcopy(original);modified={};report={}
import struct
owned={'clavicle_l','upperarm_l','lowerarm_l'}
for family in ('base','mag10'):
    modified[family]=[];report[family]={}
    for role in ('sprint_enter','sprint_loop','sprint_exit'):
        clip,entry=entry_for(family,role);duration=(clip['keys']-1)/clip['fps']
        existing={tr['bone']:tr for tr in entry['tracks']}
        times=sorted({struct.unpack('<f',struct.pack('<f',t))[0] for t in ({i/240 for i in range(round(duration*240)+1)}|{t for tr in entry['tracks'] if tr['bone'] in owned for t in tr['times']})})
        tracks={n:{'bone':n,'times':times,'values':[]} for n in names if n in owned};previous={}
        for t in times:
            progress=t/duration if role=='sprint_enter' else 1-t/duration if role=='sprint_exit' else 1.
            row,_=local_pose(clip,entry,t);fixed=align_shoulder(row,12*ease(progress/.65));raw=local_pose(clip,{'tracks':[]},t)[1]
            for n,tr in tracks.items():
                loc=fixed[parents[n]].inverted()@fixed[n];p,q,sc=(K@loc@K).decompose();bp,bq,bs=(K@raw[n]@K).decompose();dq=q@bq.inverted()
                if n in previous and dq.dot(previous[n])<0:dq=-dq
                # Keep native segment translations and all scale channels.
                # Only the shoulder origin translates to follow the upper arm.
                dp,_,ds=sample(existing[n],t) if n in existing else (Vector((0,0,0)),Quaternion(),Vector((0,0,0)))
                if n=='clavicle_l':dp=p-bp
                previous[n]=dq;tr['values'].extend([*dp,dq.x,dq.y,dq.z,dq.w,*ds])
        replacement=copy.deepcopy(entry);replacement['tracks']=[tr for tr in entry['tracks'] if tr['bone'] not in owned]+list(tracks.values())
        next(c for c in spec[family] if c['base']==entry['base']).update(replacement);modified[family].append(entry['base'])
        report[family][role]={'duration':duration,'owned_bones':sorted(owned),'shoulder_hinge_degrees':12,'ramp_end_progress':.65,'keys':len(times)}
(O/'profile_patch.json').write_text(json.dumps({'profiles':spec,'modified':modified}));(O/'author_report.json').write_text(json.dumps(report,indent=2))
for family in ('base','mag10'):
    for role in ('sprint_enter','sprint_loop','sprint_exit'):
        clip,entry=entry_for(family,role);entry=next(c for c in spec[family] if c['base']==entry['base']);duration=(clip['keys']-1)/clip['fps']
        r.animation_data_clear();r.animation_data_create();action=bpy.data.actions.new('A_M24_SprintShoulder31_'+family+'_'+role);r.animation_data.action=action;previous={}
        for i in range(round(duration*120)+1):
            row,_=local_pose(clip,entry,i/120)
            for n,m in row.items():
                loc=row[parents[n]].inverted()@m if parents[n] else m;p=r.pose.bones[n];p.rotation_mode='QUATERNION';p.matrix_basis=local_rest[n].inverted()@loc
                if n in previous and p.rotation_quaternion.dot(previous[n])<0:p.rotation_quaternion=-p.rotation_quaternion
                previous[n]=p.rotation_quaternion.copy()
                for prop in ('location','rotation_quaternion','scale'):p.keyframe_insert(prop,frame=i/4)
        action.use_fake_user=True
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_SprintShoulder_Editable.blend'))
print('M24_SPRINT_SHOULDER_AUTHORED',json.dumps({k:len(v) for k,v in modified.items()}),flush=True)
