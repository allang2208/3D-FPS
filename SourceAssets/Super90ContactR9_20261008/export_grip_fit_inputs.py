from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
out={}
for family in ('vertical','canted','prism','angled'):
 p=s['idles'][family];out[family]={'hand':np.asarray(p['hand_l']).tolist(),'local':{n:np.asarray(p[s['parents'][n]].inverted()@p[n]).tolist() for n in s['finger_names']['l']}}
(O/'grip_hand_seeds.json').write_text(json.dumps(out,indent=2));points=deform(s['idle']);np.savez_compressed(O/'gun_idle_mesh.npz',vertices=np.array([list(p) for p in points]),faces=np.array(solids['gun']))
