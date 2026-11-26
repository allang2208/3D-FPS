"""Bring the crossed hands toward the abdomen, fitting palms before fingers."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
recipe=(P/'Tools/ChapelNun/author_idle_crossed_r4.py').read_text(encoding='utf-8')
exec(compile(recipe[:recipe.index('exec(compile(source')],'<R4 authoring recipe>','exec'))
change("OUT = NUN / 'IdleCrossedR4'", "OUT = NUN / 'IdleCrossedR5Tuck'")
change('IdleRelaxedR3/Review/InputsAfter','IdleCrossedR4/Review/InputsAfter')
change("targets = {'l': np.array([6.0, 17.7, 89.5]), 'r': np.array([-4.0, 21.8, 91.0])}",
       "targets = {'l': np.array([5.0, 16.0, 89.0]), 'r': np.array([-3.0, 19.0, 91.5])}")
change("directions = {'l': unit([-.72, .16, -.68]), 'r': unit([.72, .16, -.68])}",
       "directions = {'l': unit([-.70, -.12, -.69]), 'r': unit([.72, -.12, -.67])}")
change("np.array([sign*pole_width[side], -1., 103.])", "np.array([sign*pole_width[side], 12.0, 103.])")
change('axis=unit(.55*forearm+.45*directions[side])','axis=unit(.55*forearm+.45*directions[side])')
change('zip(DIGITS, (2., 4., 6., 7.))','zip(DIGITS, (1., 2., 3., 4.))')
change('.72*tangent+.28*forward','.60*tangent+.40*forward')
change('.70*thumb+.30*aim','.60*thumb+.40*aim')
change('np.dot(direction,normal)*.65','np.dot(direction,normal)*.75')
change("torso[j, 1].max()+.8-hand_all[i, 1]", "torso[j, 1].max()+.6-hand_all[i, 1]")
change("torso[j, 1].max()+.6-hand_all[i, 1]", "torso[j, 1].max()+.35-hand_all[i, 1]")
change("    hand_all = np.concatenate([bp[hand_ids[s]] for s in ('l', 'r')])", """    hand_all = np.concatenate([bp[hand_ids[s]] for s in ('l', 'r')]+[rp[sleeve_ids[s]][np.linalg.norm(rp[sleeve_ids[s]]-w[ix['hand_'+s],:3,3],axis=1)<10] for s in ('l','r')])""")
start=source.index('# Fit the support hand')
end=source.index('# Use long-sleeve surfaces')
source=source[:start]+'''# Lay the supporting thumb along the index instead of opposing it deeply
# toward the abdomen; it must not keep the whole pair away from the robe.
for joint in (1,2):
    name=f'thumb_{joint:02d}_l';child=f'thumb_{joint+1:02d}_l'
    w=fk(base);direction=unit(w[ix[child],:3,3]-w[ix[name],:3,3])
    normal=unit(w[ix['hand_l'],:3,:3] @ hand_basis['l'][:,2])
    desired=unit(direction-normal*np.dot(direction,normal)*.55)
    orient(base,name,between(direction,desired) @ w[ix[name],:3,:3])

# Fit the palm surfaces first. The previous whole-hand maximum let a curled
# pinky hold the entire upper palm away from the lower hand.
contact_steps=[]
def columns(left,right,radius=.34):
    neighbors=cKDTree(left[:,[0,2]]).query_ball_point(right[:,[0,2]],radius)
    return [float(left[j,1].max()-right[i,1]) for i,j in enumerate(neighbors) if j]
for step in range(8):
    f=place_hands(base.copy());w=fk(f);points=body.skin(w)
    regions={}
    for side in ('l','r'):
        wrist=w[ix['hand_'+side],:3,3]
        axis=unit(w[ix['middle_01_'+side],:3,3]-wrist)
        ids=np.array([i for i in hand_ids[side] if not body.dominant[i].startswith('thumb_')]);along=(points[ids]-wrist)@axis
        regions[side]=points[ids[(along>.6)&(along<8.5)]]
    shifts=columns(regions['l'],regions['r'])
    if not shifts:raise RuntimeError('Palms must overlap before finger fitting')
    shift=max(shifts)+.10;targets['r'][1]+=shift
    contact_steps.append({'palm_shift_cm':shift})
    if abs(shift)<.012:break

# Relax individual upper fingers over the supporting hand, rather than pushing
# the pair away from the abdomen. Retain a minimum MCP/PIP bend in each digit.
for step in range(10):
    changed=False
    for digit in DIGITS:
        f=place_hands(base.copy());w=fk(f);points=body.skin(w)
        ids=np.array([i for i,n in enumerate(body.dominant) if n.startswith(digit+'_') and n.endswith('_r') and 'metacarpal' not in n])
        shifts=columns(points[hand_ids['l']],points[ids])
        required=max(shifts+[-1.])+.10
        if required<.015:continue
        normal=unit(fk(base)[ix['hand_r'],:3,:3] @ hand_basis['r'][:,2])
        moved=0.
        for joint,fraction in ((1,1.),(2,.65)):
            name=f'{digit}_{joint:02d}_r';child=f'{digit}_{joint+1:02d}_r'
            bw=fk(base);direction=unit(bw[ix[child],:3,3]-bw[ix[name],:3,3])
            if joint==1:
                bend=math.degrees(math.asin(np.clip(np.dot(direction,normal),-1.,1.)));floor=5.
            else:
                parent=f'{digit}_01_r';before=unit(bw[ix[name],:3,3]-bw[ix[parent],:3,3])
                bend=math.degrees(math.acos(np.clip(np.dot(before,direction),-1.,1.)));floor=8.
            extension=min(3.*fraction,max(0.,bend-floor))
            if extension>.01:
                rotate_world(base,name,unit(np.cross(direction,normal)),-extension);moved+=extension
        if moved>0:
            changed=True;contact_steps.append({'digit':digit,'extension_deg':moved,'step':step})
    if not changed:break
# Retain a small final skin clearance for residual fingertip/side surfaces.
for step in range(6):
    f=place_hands(base.copy());points=body.skin(fk(f))
    shifts=columns(points[hand_ids['l']],points[hand_ids['r']],.42)
    shift=max(shifts+[-1.])+.12
    if shift<.012:break
    targets['r'][1]+=shift;contact_steps.append({'final_clearance_shift_cm':shift})

'''+source[end:]
change("fit_steps=fit_steps, runtime_tested=False)","fit_steps=fit_steps, palm_contact_steps=contact_steps, runtime_tested=False)")
change('Original hands overlapping in front; low relaxed elbows and reduced wrist fold, with quiet breathing',
       'Crossed hands close to lower abdomen; palm contact before individual finger relaxation; quiet breathing')
exec(compile(source,str(P/'Tools/ChapelNun/author_idle_hands_front.py'),'exec'))
