"""Keep the original overlapping hands; relax the arm chain and side silhouette."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
source=(P/'Tools/ChapelNun/author_idle_hands_front.py').read_text(encoding='utf-8')
def change(old,new):
    global source
    if old not in source:raise RuntimeError('Authoring template changed: '+old[:60])
    source=source.replace(old,new)
change("OUT = NUN / 'IdleHandsFrontR1'", "OUT = NUN / 'IdleCrossedR4'")
change("rig = read(OUT / 'native_rig.json')", "rig = read(NUN / 'IdleHandsFrontR1/native_rig.json')")
change("NUN / 'ProductionR1/Inputs/native_body.json'", "NUN / 'IdleRelaxedR3/Review/InputsAfter/body.json'")
change("NUN / 'ProductionR1/Inputs/native_robe.json'", "NUN / 'IdleRelaxedR3/Review/InputsAfter/robe.json'")
change("zip(DIGITS, (1., 2., 3., 4.))", "zip(DIGITS, (2., 4., 6., 7.))")
change("targets = {'l': np.array([5.8, 24.8, 96.0]), 'r': np.array([-6.2, 27.0, 99.2])}",
       "targets = {'l': np.array([6.0, 17.7, 89.5]), 'r': np.array([-4.0, 21.8, 91.0])}")
change("directions = {'l': unit([-.47, .02, -.88]), 'r': unit([.64, -.015, -.77])}",
       "directions = {'l': unit([-.72, .16, -.68]), 'r': unit([.72, .16, -.68])}")
change("pole_width = {'l': 19.5, 'r': 20.0}", "pole_width = {'l': 17.5, 'r': 18.0}")
change("np.array([sign*pole_width[side], 7., 108.])", "np.array([sign*pole_width[side], -1., 103.])")
change("        orient(f, 'hand_'+side, rotations[side])", """        w=fk(f)
        forearm=unit(w[ix['hand_'+side], :3, 3]-w[ix['lowerarm_'+side], :3, 3])
        # Keep the palm axis close to the forearm, instead of independently
        # pitching both wrists downward beneath a forward-pointing sleeve.
        axis=unit(.55*forearm+.45*directions[side])
        rotations[side]=basis(axis,np.array([0.,-1.,-.03])) @ hand_basis[side].T
        orient(f, 'hand_'+side, rotations[side])""")
change("torso[j, 1].max()+1.3-hand_all[i, 1]", "torso[j, 1].max()+.8-hand_all[i, 1]")
change("# Left hand is the lower support", """# Bring the fingers closer together in the palm plane while retaining their
# native graded curl. The thumb follows the hand rather than opening away.
for side in ('l', 'r'):
    w = fk(base)
    h = ix['hand_'+side]
    forward = unit(w[ix['middle_01_'+side], :3, 3]-w[h, :3, 3])
    normal = unit(w[h, :3, :3] @ hand_basis[side][:, 2])
    for digit in ('index', 'ring', 'pinky'):
        name = f'{digit}_01_{side}'; child = f'{digit}_02_{side}'
        w = fk(base)
        direction = unit(w[ix[child], :3, 3]-w[ix[name], :3, 3])
        curl = np.dot(direction, normal)
        tangent = unit(direction-normal*curl)
        desired = unit(unit(.72*tangent+.28*forward)*math.sqrt(max(0.,1.-curl*curl))+normal*curl)
        orient(base, name, between(direction,desired) @ w[ix[name], :3, :3])
    name='thumb_01_'+side
    w=fk(base)
    thumb=unit(w[ix['thumb_03_'+side], :3, 3]-w[ix[name], :3, 3])
    aim=unit(w[ix['index_02_'+side], :3, 3]-w[ix[name], :3, 3])
    # Partial adduction, leaving the thumb relaxed and clear of the other hand.
    orient(base,name,between(thumb,unit(.70*thumb+.30*aim)) @ w[ix[name], :3, :3])

# The upper thumb must not become a rigid spacer between the overlapping palms.
for joint in (1, 2):
    name=f'thumb_{joint:02d}_r';child=f'thumb_{joint+1:02d}_r'
    w=fk(base)
    direction=unit(w[ix[child], :3, 3]-w[ix[name], :3, 3])
    normal=unit(w[ix['hand_r'], :3, :3] @ hand_basis['r'][:, 2])
    desired=unit(direction-normal*np.dot(direction,normal)*.65)
    orient(base,name,between(direction,desired) @ w[ix[name], :3, :3])

# Left hand is the lower support""")
change("('spine_02', .07), ('spine_03', .12), ('spine_04', .23), ('spine_05', .22)",
       "('spine_02', .045), ('spine_03', .08), ('spine_04', .15), ('spine_05', .14)")
change(".13*math.sin(cycle)", ".075*math.sin(cycle)")
change(".10*math.sin(2*cycle+.3)", ".06*math.sin(2*cycle+.3)")
change(".0015*breath", ".0011*breath")
change(".15*math.sin(cycle+.5)", ".08*math.sin(cycle+.5)")
change("Newly authored from user standing reference; native Kaitlin support pose", "Original hands overlapping in front; low relaxed elbows and reduced wrist fold, with quiet breathing")
exec(compile(source,str(P/'Tools/ChapelNun/author_idle_hands_front.py'),'exec'))
