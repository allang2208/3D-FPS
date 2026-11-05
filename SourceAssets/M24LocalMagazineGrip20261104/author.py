"""Bake stable magazine-local grips, with staggered curl entry and release."""
from pathlib import Path
__file__=str(Path(__file__).parent/'common.py')
exec(compile(Path(__file__).read_text(),'local grip helpers','exec'))
exec(compile((TASKOUT.parent/'M24SurfaceGrip20261103/reach.py').read_text(),'native arm reach','exec'))
grips=json.loads((TASKOUT/'grip_anchors.json').read_text())
owned=['clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l','ik_hand_l',*digits]

def envelope(f,stage,offset=0.):
    if stage=='old':return smooth((f-10-offset)/(8-offset))*(1-smooth((f-24-offset)/(4.5-offset)))
    return smooth((f-29.5-offset)/(4.5-offset))*(1-smooth((f-40-offset)/(6-offset)))

def authored(family,role,t):
    f=t*30;stage='old' if f<29 else 'new';w=envelope(f,stage)
    fr=GripFrame(family,f,role,False);row=fr.row
    if w<=1e-9:return row
    a=grips['mag10' if 'mag10' in family else 'base'][stage]
    target=fr.row['WPN_Magazine']@Matrix(a['mag_to_hand'])
    h=fr.row['hand_l'];p=h.translation.lerp(target.translation,w);q=h.to_quaternion().slerp(target.to_quaternion(),w)
    rot=q@h.to_quaternion().inverted()
    if rot.w<0:rot.negate()
    fr.basis=h.to_quaternion().to_matrix()
    x=np.r_[np.array(fr.basis.transposed()@(p-h.translation))*1000,np.array(fr.basis.transposed()@rot.axis)*math.degrees(rot.angle)]
    row,angle,shift=reach_pose(fr,x)
    for n in names:
        if n=='hand_l' or n not in handbones:continue
        pos,orientation,scale=fr.local[n].decompose()
        if n in a['digits']:
            digit=n.split('_')[0];offset={'index':0.,'middle':.18,'ring':.36,'pinky':.54}[digit]
            orientation=orientation.slerp(Quaternion(a['digits'][n]),envelope(f,stage,offset))
        row[n]=row[parents[n]]@Matrix.LocRotScale(pos,orientation,scale)
    return row

patch={};expected={};candidates=copy.deepcopy(D['profiles'])
recipe={'scope':'M24 local front grip: stable magazine-relative wrist and finger curl, accepted thumb retained',
        'svd_source':str(svd_source),'svd_reference_frame':120,'owned_bones':owned,'profiles':{},'runtime_tested':False,'preview_rendered':False}
for family in D['profiles']:
    patch[family]=[];expected[family]=[]
    for role in ('reload','reload_empty'):
        source=entry(family,role);old={tr['bone']:tr for tr in source['tracks']};clipdata=D['clips'][source['base']]
        times=sorted({f32(t) for t in [0,source['duration'],10/30,28.5/30,29.5/30,46/30,*[i/200 for i in range(66,308)],*[t for n in owned if n in old for t in old[n]['times']]]})
        tracks={n:{'bone':n,'times':times,'values':[]} for n in owned};last={}
        for t in times:
            active=envelope(t*30,'old')>1e-9 or envelope(t*30,'new')>1e-9
            if active:row=authored(family,role,t)
            for n,tr in tracks.items():
                v=list(sample(old[n],t,10,'values') if n in old else [0,0,0,0,0,0,1,0,0,0])
                if active:
                    local=row[parents[n]].inverted()@row[n];pos,q,sc=(K@local@K).decompose();bp,bq,bs=transform(raw(clipdata,t,n)).decompose()
                    dq=q@bq.inverted();dq.normalize()
                    if n in last and dq.dot(last[n])<0:dq.negate()
                    v[3:7]=[dq.x,dq.y,dq.z,dq.w]
                    if n=='ik_hand_l':v[:3]=list(pos-bp)
                last[n]=Quaternion((v[6],*v[3:6]));tr['values'].extend(f32(x) for x in v)
        change={'base':source['base'],'duration':source['duration'],'tracks':list(tracks.values())}
        patch[family].append(change);expected[family].append(copy.deepcopy(source))
        dst=next(c for c in candidates[family]['clips'] if c['base']==source['base']);replace={tr['bone']:tr for tr in change['tracks']}
        dst['tracks']=[replace.pop(tr['bone'],tr) for tr in dst['tracks']]+list(replace.values())
        recipe['profiles'][family+'/'+role]={'keys':len(times),'duration':source['duration']}
        print('M24_LOCAL_GRIP_AUTHORED',family,role,flush=True)
for name,data in [('reload_patch.json.gz',patch),('expected_profiles.json.gz',expected),('candidate_profiles.json.gz',candidates)]:
    with gzip.open(TASKOUT/name,'wt',compresslevel=1) as fp:json.dump(data,fp,separators=(',',':'))
recipe['candidate_sha256']=hashlib.sha256((TASKOUT/'candidate_profiles.json.gz').read_bytes()).hexdigest()
(TASKOUT/'authoring.json').write_text(json.dumps(recipe,indent=2))

# Reuse the native editable export, including the dynamic JC corrective actions.
DEST=TASKOUT
code='# Editable animation actions'+(TASKOUT.parent/'M24SVDThumbPalm20261102/author.py').read_text().split('# Editable animation actions',1)[1]
code=code.replace('M24_SVDPalm','M24_LocalMagazineGrip').replace('M24_SVDThumbPalm_Editable.blend','M24_LocalMagazineGrip_Editable.blend')
code=code.replace('r.animation_data_create();r.animation_data.action=action',"r.animation_data_create();r.animation_data.action=action\n        shape_action=bpy.data.actions.new(action.name+'_JC');shape_action.use_fake_user=True\n        skin.data.shape_keys.animation_data_create();skin.data.shape_keys.animation_data.action=shape_action\n        action['corrective_action']=shape_action.name")
code=code.replace("row,local=compose(entry(family,role),i/120)","row,local=compose(entry(family,role),i/120)\n            shape_weights,_=corrective_weights(row,morphs.files)\n            for shape_name in morphs.files:\n                key=skin.data.shape_keys.key_blocks[shape_name];key.value=shape_weights.get(shape_name,0.)\n                key.keyframe_insert('value',frame=i)")
code=code.replace('s.frame_start=0;s.frame_end=240',"skin.data.shape_keys.animation_data.action=bpy.data.actions['M24_LocalMagazineGrip_base_reload_JC']\ns.frame_start=0;s.frame_end=240")
exec(compile(code,'editable source export','exec'))
