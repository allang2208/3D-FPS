import json,math
from pathlib import Path
O=Path(__file__).parent;author=O.parent/'Super90Speedloader20261007/author_speedloader.py';s={'__file__':str(author)}
exec(compile(author.read_text().split('def local_rows(')[0],str(author),'exec'),s)
names=[n for n in s['names'] if 'arm' in n or n.startswith('hand_')];out=[]
for family in ('base','vertical','canted','prism','angled'):
 for empty in (False,True):
  for count in range(1,8):
    initial=s['pose'](0,count,empty,family)[0]
    previous=initial;maximum={n:(0.,0) for n in names}
    for f in range(1,s['duration'](count,empty)+1):
        p=s['pose'](f,count,empty,family)[0]
        for n in names:
            a=p[n].to_quaternion().rotation_difference(previous[n].to_quaternion()).angle;a=math.degrees(min(a,2*math.pi-a))
            if a>maximum[n][0]:maximum[n]=(a,f)
        previous=p
    out.append({'family':family,'count':count,'empty':empty,'max_rotation_step':maximum})
    endpoint=s['pose'](s['duration'](count,empty),count,empty,family)[0]
    errors={}
    for n in names:
        a=endpoint[n].to_quaternion().rotation_difference(initial[n].to_quaternion()).angle
        errors[n]=math.degrees(min(a,2*math.pi-a))
    out[-1]['end_rotation_error_degrees']=errors
(O/'Diagnostics/twist_check.json').write_text(json.dumps(out,indent=2))
print('TWIST_MAX',sorted([(v[0],r['count'],r['empty'],n,v[1]) for r in out for n,v in r['max_rotation_step'].items()],reverse=True)[:8])
print('END_MAX',max((v,n,r['count'],r['empty']) for r in out for n,v in r['end_rotation_error_degrees'].items()))
