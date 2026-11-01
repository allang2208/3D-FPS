from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text().split("if __name__=='__main__':")[0],'library','exec'))
import numpy as np
idle,_=pose('idle',0);M=rest['WPN_root']@idle['WPN_root'].inverted()
pts=np.array([v.co[:] for v in bpy.data.objects['M24_base'].data.vertices]);result={'idle_hand_source':{n:list(M@idle[n].translation) for n in names if under(n,'hand_r')},'body_min':pts.min(0).tolist(),'body_max':pts.max(0).tolist(),'sections':[]}
for y in np.arange(-.38,.15,.02):
 p=pts[(pts[:,1]>=y)&(pts[:,1]<y+.02)]
 if len(p):result['sections'].append({'y':round(float(y),3),'min':p.min(0).tolist(),'max':p.max(0).tolist()})
(O/'hand_layout.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
_,loc=pose('idle',0)
print('FINGER_BASIS',{n:[round(math.degrees(v),1) for v in (local_rest[n].inverted()@loc[n]).to_euler()] for n in names if n.endswith('_r') and any(n.startswith(d+'_') for d in ('index','middle','ring','pinky','thumb'))},flush=True)
