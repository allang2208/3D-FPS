"""Inspect saved RSH reload mechanics at the existing contact times; no game run."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
sys.path.insert(0,str(O.parent/'RSH12InspectGrip20261004'))
from grip_scene import load,pose
sys.path.insert(0,str(O.parent/'RSH12Speedloader20261003'))
from contact_motion import skin_anchor
fit=json.loads((O.parent/'RSH12Fit20261003/fit_contract.json').read_text())
recipe=json.loads((O.parent/'RSH12ContactRepair20261003/single_contacts.json').read_text())
out={}
for side in ('single','r','l'):
    rig,data,authored,meta=load(side)
    files=['DA_RSH12_'+('' if side=='single' else side+'_')+'base']
    if side=='single':files+=['DA_RSH12_'+f for f in ('angled','vertical','canted','prism')]
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones};newrest={n:Matrix(v) for n,v in meta['mechanical_bind_matrices'].items()}
    align=Matrix(meta['alignment']);canonical=rest['WPN_root']@align
    for name in files:
        profile=json.loads((O/'Before'/(name+'.json')).read_text());byasset={c['base']:c for c in authored['clips']}
        for entry in profile['clips']:entry['kind']=byasset[entry['base']]['kind']
        rows=[]
        for kind,clip in data['clips'].items():
            if not kind.startswith(('single_','speed_')):continue
            speed=kind=='speed_0';start,count=(0,5) if speed else map(int,kind.split('_')[1:])
            for i in range(start,min(5,start+count)):
                contact=2.42/3.6*clip['duration'] if speed else (1.5 if start==0 else .6)+1.1*(i-start)+.64
                # First source sample at or after the actual ammo commit.
                sample=next(s for s in clip['samples'] if s['time']>=contact-1e-6)
                p=pose(rig,data,profile,kind,sample)
                bone='WPN_Case_'+str(i)
                case=p[bone]@newrest[bone].inverted()@canonical
                cylinder=p['WPN_Cylinder']@newrest['WPN_Cylinder'].inverted()@canonical
                x,z,_=fit['chambers'][i]['center_xz_radius'];point=Vector((x,fit['rear_plane_m'],z))
                error=((case@point)-(cylinder@point)).length*1000
                axis=math.degrees((case.to_3x3()@Vector((0,1,0))).angle(cylinder.to_3x3()@Vector((0,1,0))))
                rows.append(dict(kind=kind,chamber=i,time=sample['time'],rim_error_mm=error,axis_error_deg=axis))
        out[name]=dict(contacts=rows,worst_rim_error_mm=max(v['rim_error_mm'] for v in rows),worst_axis_error_deg=max(v['axis_error_deg'] for v in rows))
        print('RSH_RELOAD_CONTACTS',name,len(rows),out[name]['worst_rim_error_mm'],out[name]['worst_axis_error_deg'],flush=True)
(O/'reload_diagnosis.json').write_text(json.dumps(out,indent=2))
