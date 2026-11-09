"""Read the current contact frame for palm-placement authoring."""
from pathlib import Path
import pickle,numpy as np
from motion import *
r=Path(__file__).resolve().parent
ns={'__file__':str(r/'author.py'),'__name__':'contact_layout'}
exec(compile((r/'author.py').read_text().split('poses=[];hands=[]')[0],str(r/'author.py'),'exec'),ns)
old=pickle.load(open(r.parent/'Repair10/authored_world.pkl','rb'));i=42
p={n:w for n,w in zip(old['names'],old['world'][i])};h=p['hand_l']
f=unit(p['middle_01_l'][:3,3]-h[:3,3]);l=unit(p['index_01_l'][:3,3]-p['pinky_01_l'][:3,3]);n=unit(np.cross(f,l));basis=np.stack((f,l,n),axis=1)
root=p['WPN_root'];legq=blend(ns['closed'],np.eye(3),.5);rq=rot(root)
rodworld=(ns['rod']@legq.T+ns['pivot'])@rq.T+root[:3,3]
axis=unit(rq@legq@ns['tip']);center=root[:3,3]+rq@ns['pivot']+axis*10.5
print('palm frame: forward, across, normal')
print('rod center',np.round((center-h[:3,3])@basis,3),'axis',np.round(axis@basis,3))
for digit in ('thumb','index','middle','ring','pinky'):
    for joint in (1,2,3):
        name=f'{digit}_{joint:02d}_l';v=p[name][:3,3]
        local=np.linalg.inv(p[ns['parents'][name]])@p[name]
        print(name,np.round((v-h[:3,3])@basis,3),'euler',np.round(R.from_matrix(rot(local)).as_euler('xyz',degrees=True),1))
print('palm vertices range',len(ns['surface_ids']))
