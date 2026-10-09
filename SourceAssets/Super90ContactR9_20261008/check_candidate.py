from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
out=[]
for empty,frames in ((False,(0,10,20,42,74,87,100,114,118,122,128,138,146)),(True,(130,140,146,158,165,174,182))):
 for f in frames:
    p=s['pose'](f,7,empty)[0];r={'frame':f,'empty':empty,'swing':wrist_swing(p,'l'),'collision':collision(p,74<=f<127)}
    out.append(r);print('FRAME',r,flush=True)
(O/'Diagnostics/candidate_contact.json').write_text(json.dumps(out,indent=2))
