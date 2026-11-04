# Build an open hand from actual phalanx directions. The reference rest fingers
# are curled, so blending toward rest alone does not produce an open palm.
hand_rest=rest['hand_l'];inv_hand=np.linalg.inv(hand_rest)
knuckles={d:(inv_hand@np.r_[rest[d+'_01_l'][:3,3],1.])[:3] for d in ['index','middle','ring','pinky']}
forward=unit(np.mean(list(knuckles.values()),axis=0))
across=knuckles['index']-knuckles['pinky'];across=unit(across-forward*(across@forward))
normal=unit(np.cross(forward,across))
axis=blade0;nearest=p0+axis*((idle['hand_l'][:3,3]-p0)@axis)
if (rotation(idle['hand_l'])@normal)@(nearest-idle['hand_l'][:3,3])<0:normal=-normal;across=-across
palm_basis=np.column_stack([forward,across,normal])
open_pose={n:np.linalg.inv(hand_rest)@rest[n] for n in names if n.endswith('_l') and n.split('_')[0] in ['thumb','index','middle','ring','pinky']}
open_local={}
for digit,spread in [('index',.10),('middle',.025),('ring',-.045),('pinky',-.13)]:
    for j in [1,2,3]:
        n=f'{digit}_{j:02d}_l';parent=parents[n]
        m=open_pose[parent]@local_rest[n]
        child=f'{digit}_{j+1:02d}_l'
        rest_axis=unit(rest[child][:3,3]-rest[n][:3,3]) if j<3 else unit(rest[n][:3,3]-rest[parent][:3,3])
        local_axis=rotation(rest[n]).T@rest_axis
        target=unit(forward+across*spread+normal*(.025 if j==1 else .06 if j==2 else .10))
        m[:3,:3]=between(rotation(m)@local_axis,target)@m[:3,:3]
        open_pose[n]=m;open_local[n]=np.linalg.inv(open_pose[parent])@m

# Place the centre of the palm, not the wrist, against the visible blade face.
# Derive the pad from the current V9 skin in the author hand's local frame.
skin_folder=P.parent/'RhythmV4/Preview20261104/Native/Standard'
skin_data=json.loads((skin_folder/'surface.json').read_text(encoding='utf-8-sig'))
bind=np.fromfile(skin_folder/'arms.bind',dtype=np.float32).reshape(-1,3)*[.01,-.01,.01]
labels=np.array(skin_data['bone_names'])[np.fromfile(skin_folder/'arms.mainbone',dtype=np.uint16)]
hp=(bind[labels=='hand_l']-hand_rest[:3,3])@rotation(hand_rest)
f=hp@forward;a=hp@across;n=hp@normal
pad=hp[(f>.025)&(f<.070)&(np.abs(a)<.027)]
pad=pad[(pad@normal)>np.quantile(pad@normal,.70)]
palm=pad.mean(axis=0)
