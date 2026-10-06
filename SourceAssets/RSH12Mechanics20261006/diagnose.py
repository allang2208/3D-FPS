"""Measure the active author's rigid mechanical frames against the real barrel."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
sys.path.insert(0,str(O.parent/'RSH12InspectGrip20261004'))
from grip_scene import load,pose
report={}
for side in ('single','r','l'):
    rig,data,profile,meta=load(side)
    file=O.parent/('RSH12UnifiedGrip20261004/Single/profile.json' if side=='single' else 'RSH12DualReloadDrop20261004/'+side+'/profile.json')
    profile=json.loads(file.read_text())
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    align=Matrix(meta['alignment']); newrest={n:Matrix(v) for n,v in meta['mechanical_bind_matrices'].items()}
    rows=[]
    for kind in ('idle','aim','fire','single_0_5','single_3_2','speed_0','inspect'):
        if kind not in data['clips']:continue
        clip=data['clips'][kind]
        for fraction in ((0,.15,.3,.5,.75,1) if kind.startswith(('single','speed','fire')) else (0,)):
            sample=min(clip['samples'],key=lambda s:abs(s['time']-fraction*clip['duration']))
            p=pose(rig,data,profile,kind,sample)
            frame=p['WPN_root']@align
            row=dict(kind=kind,time=sample['time'],bones={})
            for bone in ('WPN_Crane','WPN_Cylinder','WPN_Extractor','WPN_Case_0'):
                effect=frame.inverted()@p[bone]@newrest[bone].inverted()@rest['WPN_root']@align
                axis=(effect.to_3x3()@Vector((0,1,0))).normalized()
                row['bones'][bone]=dict(axis=list(axis),barrel_angle_deg=math.degrees(axis.angle(Vector((0,1,0)))),matrix=[list(v) for v in effect])
            rows.append(row)
            print('MECHANISM',side,kind,round(sample['time'],3),[(n,round(v['barrel_angle_deg'],4)) for n,v in row['bones'].items()],flush=True)
    report[side]=rows
(O/'diagnosis_source.json').write_text(json.dumps(report,indent=2))
