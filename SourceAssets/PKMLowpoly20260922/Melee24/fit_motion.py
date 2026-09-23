"""Fit a PKM-specific buttstock arc to both arms, using only each PKM idle.

The stock leads the diagonal strike; the long barrel sweeps left and down.
This adjusts the rigid gun/hand group, never slides a palm on its grip.
"""
import json, math
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation, Slerp

O=Path(__file__).parent
sources=json.loads((O/'grips.json').read_text())
STOCK=np.array([-.00003818,.359063,-.027])
FPS=120
# Cadence follows the existing rifles. These are new PKM positions/orientations,
# not the short QBZ stock displacement translated onto the longer PKM stock.
TIMES=np.array([0.,.035,.100,1/6,.205,.285,.420,.600,.760,.860,.900])
ANGLES=np.array([[0,0,0],[-3,-3,24],[-11,-12,86],[-15,-14,125],
                 [-17,-15,128],[-13,-13,116],[-10,-10,91],[-6,-8,43],
                 [-2,-2,10],[0,0,0],[0,0,0]],float)
STOCK_PATH=np.array([[0,0,0],[.045,.105,.010],[.120,.380,.055],
                     [.005,.510,.105],[-.010,.500,.100],[.015,.455,.085],
                     [.140,.355,.045],[.150,.160,-.010],[.035,.025,-.005],
                     [0,0,0],[0,0,0]],float)
SHOULDER_OFFSETS={'r':np.array([.115,-.030,-.220]),'l':np.array([-.015,-.065,-.040])}
times=np.arange(109)/FPS
angles=PchipInterpolator(TIMES,ANGLES,axis=0)(times)
travel=PchipInterpolator(TIMES,STOCK_PATH,axis=0)(times)

def smooth(x):
    x=np.clip(x,0,1); return x*x*(3-2*x)

result={}
for family,data in sources.items():
    idle={k:np.array(v) for k,v in data['idle'].items()}
    rest={k:np.array(v) for k,v in data['rest'].items()}
    w0=idle['WPN_root']; inv=np.linalg.inv(w0)
    stock0=w0[:3,:3]@STOCK+w0[:3,3]
    hands={s:inv@idle['hand_'+s] for s in 'rl'}
    shoulders={s:idle['upperarm_'+s][:3,3] for s in 'rl'}
    lengths={s:tuple(np.linalg.norm(idle[b+'_'+s][:3,3]-idle[a+'_'+s][:3,3])
                    for a,b in [('upperarm','lowerarm'),('lowerarm','hand')]) for s in 'rl'}
    fore={s:rest['hand_'+s][:3,3]-rest['lowerarm_'+s][:3,3] for s in 'rl'}
    fore={s:v/np.linalg.norm(v) for s,v in fore.items()}
    refs={s:np.linalg.inv(rest['hand_'+s][:3,:3])@fore[s] for s in 'rl'}
    previous=np.zeros(6); values=[]; seeds=[]
    def info(Q,P,s):
        H=hands[s]; wr=Q@H[:3,3]+P-Q@STOCK
        sh=shoulders[s]; a,b=lengths[s]; v=wr-sh; d=np.linalg.norm(v); axis=v/d
        along=(a*a-b*b+d*d)/(2*d); radius=math.sqrt(max(0,a*a-along*along))
        natural=Q@H[:3,:3]@refs[s]; natural/=np.linalg.norm(natural)
        pole=-natural+axis*np.dot(natural,axis); pole/=max(1e-8,np.linalg.norm(pole))
        el=sh+axis*along+pole*radius; f=wr-el; f/=np.linalg.norm(f)
        bend=math.acos(np.clip(np.dot(natural,f),-1,1))
        crossing=max(0,(sh[0]-el[0])*(1 if s=='r' else -1)-.03)
        return bend,d/(a+b),crossing,wr,el
    for i,t in enumerate(times):
        Q=Rotation.from_euler('xyz',angles[i],degrees=True).as_matrix()@w0[:3,:3]
        P=stock0+travel[i]
        weight=smooth(t/.075)*(1-smooth((t-.67)/.19))
        shoulders={s:idle['upperarm_'+s][:3,3]+SHOULDER_OFFSETS[s]*weight for s in 'rl'}
        def residual(x):
            q=Rotation.from_rotvec(x[:3]).as_matrix()@Q
            p=P+x[3:]
            res=[]
            for s in 'rl':
                bend,reach,crossing,wr,el=info(q,p,s)
                # Penalize the impossible arm triangle and actual wrist flexion,
                # not just a hand bone's Euler angle.
                res.extend([18*max(0,bend-math.radians(27)), .15*bend,
                            100*max(0,reach-.93), 20*crossing])
                if s=='r':res.append(18*weight*max(0,el[2]+.14))
            res.extend(.75*x[:3]); res.extend(7*x[3:])
            res.extend(.8*(x[:3]-previous[:3]));res.extend(9*(x[3:]-previous[3:]))
            # A buttstock strike needs a leading rear end, not a side slap.
            stock_normal=q@np.array([0,1,0])
            contact=smooth((t-.09)/.055)*(1-smooth((t-.28)/.18))
            res.extend([5*contact*max(0,.48-stock_normal[1]),
                        30*contact*max(0,.100-p[1]),
                        35*contact*max(0,-.045-p[2]),
                        18*weight*max(0,.82-q[2,2]),
                        20*contact*max(0,p[1]-.170)])
            return res
        cap=np.array([.62,.78,.50,.080,.10,.080])*max(weight,1e-7)
        if weight<1e-6:
            x=np.zeros(6)
        else:
            x=least_squares(residual,np.clip(previous,-cap*.999,cap*.999),bounds=(-cap,cap),
                            max_nfev=80,ftol=2e-6,xtol=2e-6,gtol=2e-6).x
        previous=x.copy(); seeds.append(x)
    # Smooth the fitted corrections, retaining the authored stock strike clock.
    corrections=gaussian_filter1d(np.array(seeds),1.5,axis=0,mode='nearest')
    for i,t in enumerate(times):
        weight=smooth(t/.035)*(1-smooth((t-.78)/.08))
        support=smooth(t/.075)*(1-smooth((t-.67)/.19))
        shoulders={s:idle['upperarm_'+s][:3,3]+SHOULDER_OFFSETS[s]*support for s in 'rl'}
        x=corrections[i]*weight
        Q=Rotation.from_rotvec(x[:3]).as_matrix()@Rotation.from_euler('xyz',angles[i],degrees=True).as_matrix()@w0[:3,:3]
        P=stock0+travel[i]+x[3:]
        W=np.eye(4);W[:3,:3]=Q;W[:3,3]=P-Q@STOCK
        if i==0 or t>=.86:W=w0.copy()
        values.append({'frame':i,'root':W.tolist(),'stock':(W[:3,:3]@STOCK+W[:3,3]).tolist(),
                       'min_wrist_deg':{s:math.degrees(info(W[:3,:3],W[:3,:3]@STOCK+W[:3,3],s)[0]) for s in 'rl'}})
    result[family]=values
    print(family,'max_min_bend', {s:round(max(v['min_wrist_deg'][s] for v in values),1) for s in 'rl'},
          'stock_contact',values[20]['stock'],flush=True)
(O/'motion.json').write_text(json.dumps(result,indent=2))
(O/'design.json').write_text(json.dumps({'fps':FPS,'duration':.9,'contact':1/6,'stock_root_m':STOCK.tolist(),
    'times':TIMES.tolist(),'angles_xyz_degrees':ANGLES.tolist(),'stock_travel_m':STOCK_PATH.tolist(),
    'shoulder_offsets_m':{s:v.tolist() for s,v in SHOULDER_OFFSETS.items()},
    'sources':'Own PKM grips; M4 N/QBZ191 O cadence and whole-chain method only'},indent=2))
