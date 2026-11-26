"""Author relaxed arms at the sides, using the retained native robe surfaces."""
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME')
# Reuse the native FK, anatomical hand bases and skinned-surface authoring code.
# Stop before the older clasped-hand pose is constructed.
helper=(P/'Tools/ChapelNun/author_idle_hands_front.py').read_text(encoding='utf-8')
helper=helper[:helper.index('body = Surface')]
helper=helper.replace("OUT = NUN / 'IdleHandsFrontR1'", "OUT = NUN / 'IdleRelaxedR3'")
helper=helper.replace("rig = read(OUT / 'native_rig.json')", "rig = read(NUN / 'IdleHandsFrontR1/native_rig.json')")
exec(compile(helper,'<native idle authoring helpers>','exec'))

body=Surface(NUN/'IdleBackReviewR2/InputsAfter/body.json')
robe=Surface(NUN/'IdleBackReviewR2/InputsAfter/robe.json')
previous=read(NUN/'IdleHandsFrontR2/authored.json')
base=np.asarray(previous['frames'][0],dtype=float)
bind=fk(reference)
# Keep the approved standing feet and gaze. Relax the complete arm chains,
# including all twist/corrective children and the native graded finger curl.
for i,name in enumerate(names):
    if name.startswith(('clavicle_','upperarm_','lowerarm_','hand_','thumb_','index_','middle_','ring_','pinky_')):
        base[i]=reference[i]
for side,sign in (('l',1),('r',-1)):
    rotate_world(base,'clavicle_'+side,[0,1,0],sign*1.15)

hand_basis={};hand_ids={};sleeve_ids={}
sleeve_vertices=np.unique(np.concatenate([robe.material_vertices[m] for m in (1,2,3)]))
for side in ('l','r'):
    h=ix['hand_'+side]
    p=lambda name:bind[ix[name+'_'+side],:3,3]
    forward=unit(p('middle_01')-p('hand'))
    normal=unit(np.cross(p('index_01')-p('pinky_01'),forward))
    if np.dot(unit(p('middle_03')-p('middle_02'))-unit(p('middle_02')-p('middle_01')),normal)<0:
        normal*=-1
    hand_basis[side]=basis(bind[h,:3,:3].T@forward,bind[h,:3,:3].T@normal)
    hand_ids[side]=np.array([i for i,n in enumerate(body.dominant) if n.endswith('_'+side) and n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_'))])
    sleeve_ids[side]=np.array([i for i in sleeve_vertices if robe.dominant[i].endswith('_'+side)])
    # Preserve native fingers instead of the extra gripping curl in R2.
    # A slight right-hand difference avoids a mirrored mannequin pose.
    if side=='r':
        for digit,angle in (('index',-.8),('middle',.5),('ring',1.0),('pinky',1.5)):
            n=f'{digit}_01_{side}';w=fk(base)
            axis=unit(np.cross(unit(w[ix[f'{digit}_02_{side}'],:3,3]-w[ix[n],:3,3]),normal))
            rotate_world(base,n,axis,angle)

shoulders=fk(base)
# Component frame is centimetres, +Y forward. Slightly different wrist heights
# and small elbow flexion keep the silhouette easy rather than ceremonial.
targets={'l':np.array([22.4,4.0,80.4]),'r':np.array([-22.0,4.7,80.9])}
pole_width={'l':21.0,'r':20.7}
torso_ids=np.unique(np.concatenate([robe.material_vertices[m] for m in (0,4,7,10)]))

def forearm_twist(f,side):
    w=fk(f);forearm=ix['lowerarm_'+side];hand=ix['hand_'+side]
    delta=R.from_matrix(w[forearm,:3,:3].T@w[hand,:3,:3]@R.from_quat(reference[hand,3:7]).as_matrix().T).as_quat()
    axis=unit(reference[hand,:3]);q=np.r_[axis*np.dot(delta[:3],axis),delta[3]];q/=max(np.linalg.norm(q),1e-9)
    if q[3]<0:q*=-1
    rv=R.from_quat(q).as_rotvec()
    for suffix,amount in (('01',.72),('02',.34)):
        i=ix[f'lowerarm_twist_{suffix}_{side}']
        f[i,3:7]=(R.from_rotvec(rv*amount)*R.from_quat(reference[i,3:7])).as_quat()

def place_arms(f,phase=0.,breath=0.):
    for side,sign in (('l',1),('r',-1)):
        w=fk(f);shoulder=w[ix['upperarm_'+side],:3,3]
        drift=(shoulder-shoulders[ix['upperarm_'+side],:3,3])*.65
        lag=phase+(.24 if side=='l' else -.19)
        drift+=np.array([sign*.035*math.sin(lag),.045*math.sin(3*lag),.045*breath])
        target=targets[side]+drift
        # An anatomical elbow bends behind the shoulder-to-wrist line; it is
        # never forced forward as in the former presenting/clasped pose.
        solve_limb(f,['upperarm_'+side,'lowerarm_'+side,'hand_'+side],target,
                   np.array([sign*pole_width[side],-12.,104.]))
        w=fk(f)
        forward=unit(w[ix['hand_'+side],:3,3]-w[ix['lowerarm_'+side],:3,3])
        forward=unit(forward+np.array([-sign*.018,.012,0.]))
        palm=np.array([-sign,.18,.015])
        orient(f,'hand_'+side,basis(forward,palm)@hand_basis[side].T)
        forearm_twist(f,side)
    return f

# Author the clearance against the actual saved robe: move the entire arm,
# never shrink sleeves, hide the hands, or bend the wrist to dodge the cloth.
fit_steps=[]
for step in range(10):
    f=place_arms(base.copy());w=fk(f);rp=robe.skin(w);bp=body.skin(w)
    adjustments={}
    for side,sign in (('l',1),('r',-1)):
        torso=rp[torso_ids];torso=torso[(sign*torso[:,0]>0)&(torso[:,2]>58)&(torso[:,2]<100)]
        tree=cKDTree(torso[:,[1,2]])
        wrist=w[ix['hand_'+side],:3,3]
        cuff=rp[sleeve_ids[side]];cuff=cuff[(np.linalg.norm(cuff-wrist,axis=1)<11.)&(cuff[:,2]<96)]
        correction=0.
        for points,gap in ((bp[hand_ids[side]],.45),(cuff,.55)):
            neighbors=tree.query_ball_point(points[:,[1,2]],.65)
            for point,ids in zip(points,neighbors):
                if ids:correction=max(correction,float(np.max(sign*torso[ids,0])+gap-sign*point[0]))
        if correction>.015:
            shift=min(correction+.04,.9)
            targets[side][0]+=sign*shift
            # Preserve a softly bent arm when the robe requires more width.
            start=shoulder=shoulders[ix['upperarm_'+side],:3,3]
            chain=bind[[ix['upperarm_'+side],ix['lowerarm_'+side],ix['hand_'+side]],:3,3]
            reach=np.linalg.norm(chain[1]-chain[0])+np.linalg.norm(chain[2]-chain[1])-.50
            horizontal=np.linalg.norm((targets[side]-start)[:2])
            targets[side][2]=max(targets[side][2],start[2]-math.sqrt(max(0.,reach*reach-horizontal*horizontal)))
            adjustments[side]=shift
    fit_steps.append(adjustments)
    if not adjustments:break

duration,rate=12.,30;frames=[]
for k in range(round(duration*rate)+1):
    cycle=math.tau*k/(duration*rate)
    breath=(math.sin(3*cycle)+.12*math.sin(6*cycle-.35))*(1.+.05*math.sin(cycle+.6))
    f=base.copy()
    for bone,amount in (('spine_02',.045),('spine_03',.08),('spine_04',.15),('spine_05',.14)):
        rotate_world(f,bone,[1,0,0],amount*breath)
    rotate_world(f,'spine_03',[0,1,0],.065*math.sin(cycle))
    rotate_world(f,'spine_05',[0,0,1],.045*math.sin(2*cycle+.3))
    f[ix['spine_04'],8:10]*=1.+.0011*breath
    for side,sign in (('l',1),('r',-1)):
        rotate_world(f,'clavicle_'+side,[0,1,0],sign*.08*breath)
    rotate_world(f,'neck_01',[1,0,0],-.09*breath)
    rotate_world(f,'head',[1,0,0],.035*breath)
    rotate_world(f,'head',[0,0,1],.07*math.sin(cycle+.5))
    place_arms(f,cycle,breath)
    frames.append(f)
frames[-1]=frames[0].copy();data=np.asarray(frames)
for k in range(1,len(data)):
    flip=np.sum(data[k-1,:,3:7]*data[k,:,3:7],axis=1)<0
    data[k,flip,3:7]*=-1
out=dict(mesh=rig['mesh'],skeleton=rig['skeleton'],names=names,parents=parents,reference=rig['reference'],rate=rate,duration=duration,
         frames=data.tolist(),source='Nun arms relaxed at the sides; supplied side-view feedback; native finger curl and low-amplitude breathing',
         source_idle=previous['source_idle'],root_motion=False,hand_targets_cm={s:t.tolist() for s,t in targets.items()},
         fit_steps=fit_steps,body_source=str(NUN/'IdleBackReviewR2/InputsAfter/body.json'),robe_source=str(NUN/'IdleBackReviewR2/InputsAfter/robe.json'),runtime_tested=False)
(OUT/'authored.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
image=Path('C:/Users/allan/AppData/Local/Temp/codex-clipboard-960954da-0bfe-4cb9-948f-1d62d6a83fd3.png')
if image.exists():shutil.copy2(image,OUT/'standing_reference.png')
print('NUN_RELAXED_IDLE_AUTHORED',len(frames),out['hand_targets_cm'],'fit',fit_steps,flush=True)
