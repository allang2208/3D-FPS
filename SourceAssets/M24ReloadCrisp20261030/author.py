"""M24: normal-reload gun anchor, synchronized decisive extraction, native V9 rig."""
from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))

original=copy.deepcopy(ue['profiles']);spec=copy.deepcopy(original);modified={};report={}
START=18.;END=25.25
# These are source-pose samples, not a second gameplay clock. Keep the existing
# magazine-out contact at 21, release at 25.25, and the 29-30 retrieval gap.
KNOTS=[(18.,18.),(19.75,19.),(21.,21.),(22.,22.6),(24.,24.3),(25.25,25.25)]
def source_frame(f):
    if f<=START or f>=END:return f
    slopes=[(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(KNOTS,KNOTS[1:])]
    tangents=[1.]+[2*a*b/(a+b) for a,b in zip(slopes,slopes[1:])]+[1.]
    i=next(i for i in range(len(KNOTS)-1) if f<=KNOTS[i+1][0])
    x,y=KNOTS[i];xx,yy=KNOTS[i+1];d=xx-x;u=(f-x)/d
    return (2*u**3-3*u*u+1)*y+(u**3-2*u*u+u)*d*tangents[i]+(-2*u**3+3*u*u)*yy+(u**3-u*u)*d*tangents[i+1]

left={n for n in names if under(n,'clavicle_l') or under(n,'WPN_Magazine') or n=='ik_hand_l'}
support={n for n in names if under(n,'clavicle_l') or n=='ik_hand_l'}
def desired(clip,entry,normal,nentry,f,is_empty):
    row,locs=local_pose(clip,entry,f/30)
    if START<f<END:
        timed,_=local_pose(clip,entry,source_frame(f)/30)
        registration=row['WPN_root']@timed['WPN_root'].inverted()
        for n in names:
            if n in left:row[n]=registration@timed[n]
    if is_empty:
        normal_row=local_pose(normal,nentry,min(f,normal['keys']-1)/30)[0]
        target=normal_row['WPN_root']
        correction=target@row['WPN_root'].inverted()
        # Move the complete common root: bolt, right fingers and support hand
        # keep their approved weapon-relative contact, without changing lengths.
        for n in names:
            if under(n,'VM_Root'):row[n]=correction@row[n]
        if f>=54:
            # Old tuck compensation swings the shoulder despite an already
            # stationary support palm. Reuse the normal hold's complete chain.
            for n in support:row[n]=normal_row[n].copy()
    return row

for family in ('base','mag10'):
    modified[family]=[];report[family]={};normal,nentry=entry_for(family,'reload')
    for role in ('reload','reload_empty'):
        clip,entry=entry_for(family,role);is_empty=role=='reload_empty';owned=left|({'VM_Root'} if is_empty else set())
        old_tracks={tr['bone']:tr for tr in entry['tracks']};accum=[]
        # Retain original keys outside extraction. Dense contact samples plus
        # mapped donor breakpoints avoid a finger/prop slip between baked keys.
        grid={i/480 for i in range(int(START*16),int(END*16)+1)}
        donor_frames={i/4 for i in range(int(START*4),int(END*4)+1)}
        for donor_frame in donor_frames:
            lo,hi=START,END
            for _ in range(40):
                mid=(lo+hi)/2
                if source_frame(mid)<donor_frame:lo=mid
                else:hi=mid
            grid.add((lo+hi)/60)
        if is_empty:grid|={i/120 for i in range((clip['keys']-1)*4+1)}
        times=sorted(grid|{t for n,tr in old_tracks.items() if n in owned for t in tr['times']}|{0.,(clip['keys']-1)/30})
        rows={t:desired(clip,entry,normal,nentry,t*30,is_empty) for t in times}
        raw_locals={t:local_pose(clip,{'tracks':[]},t)[1] for t in times}
        for n in names:
            if n not in owned:continue
            tr={'bone':n,'times':times,'values':[]};prev=None
            for t in times:
                if n!='VM_Root' and not START<t*30<END and not (is_empty and n in support and t*30>=54):
                    p,q,sc=sample(old_tracks[n],t) if n in old_tracks else (Vector((0,0,0)),Quaternion(),Vector((0,0,0)))
                else:
                    row=rows[t];loc=row[parents[n]].inverted()@row[n] if parents[n] else row[n]
                    p,q,sc=(K@loc@K).decompose()
                    raw=raw_locals[t][n];bp,bq,bs=(K@raw@K).decompose()
                    p-=bp;q=q@bq.inverted();sc-=bs
                if prev is not None and prev.dot(q)<0:q=-q
                prev=q.copy();tr['values'].extend([*p,q.x,q.y,q.z,q.w,*sc])
            accum.append(tr)
        replacement=copy.deepcopy(entry);replacement['tracks']=[tr for tr in entry['tracks'] if tr['bone'] not in owned]+accum
        next(c for c in spec[family] if c['base']==entry['base']).update(replacement)
        modified[family].append(entry['base']);report[family][role]={'changed_bones':sorted(owned),'duration':entry['duration'],'extraction_source_knots':KNOTS,'gun_reference':'normal reload, then its final hold' if is_empty else 'unchanged'}

(O/'profile_patch.json').write_text(json.dumps({'profiles':spec,'modified':modified}))
(O/'author_report.json').write_text(json.dumps(report,indent=2))
# Store editable actions on the same V9 rig; production uses the profile patch.
for family in ('base','mag10'):
    for role in ('reload','reload_empty'):
        clip,entry=entry_for(family,role);entry=next(c for c in spec[family] if c['base']==entry['base'])
        r.animation_data_clear();r.animation_data_create();action=bpy.data.actions.new('A_M24_Crisp30_'+family+'_'+role);r.animation_data.action=action
        edit_times=sorted({i/120 for i in range((clip['keys']-1)*4+1)}|{t for tr in entry['tracks'] for t in tr['times'] if START<=t*30<=END})
        for t in edit_times:
            row,_=local_pose(clip,entry,t)
            for n,m in row.items():
                loc=row[parents[n]].inverted()@m if parents[n] else m;p=r.pose.bones[n];p.rotation_mode='QUATERNION';p.matrix_basis=local_rest[n].inverted()@loc
                for prop in ('location','rotation_quaternion','scale'):p.keyframe_insert(prop,frame=t*30)
        action.use_fake_user=True
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_ReloadCrisp_Editable.blend'))
print('M24_RELOAD_CRISP_AUTHORED',json.dumps({k:len(v) for k,v in modified.items()}),flush=True)
