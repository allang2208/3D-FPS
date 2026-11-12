"""Verify joint-only ownership against the currently saved Wrist33 followup."""
from fit_hold import *
rows={};failures=[];allowed={names[i] for i in [cl]+arm+[ha]}
for family in ['base','vertical','angled','canted','prism','bipod']:
    old=profile(family);new=json.load(gzip.open(root/(family+'.json.gz'),'rt'))
    for row in new['clips']:
        path=row['base'];c=d['clips'].get(path)
        if c is None:continue
        t=np.array(c['times']);base=np.array(c['frames']);a=layer(base,path,old,names,t);b=layer(base,path,new,names,t)
        others=[i for i,n in enumerate(names) if n not in allowed]
        delta=(R.from_quat(a[:,others,3:7].reshape(-1,4)).inv()*R.from_quat(b[:,others,3:7].reshape(-1,4))).magnitude()
        result=dict(local_translation_error=float(abs(a[:,:,:3]-b[:,:,:3]).max()),local_scale_error=float(abs(a[:,:,7:]-b[:,:,7:]).max()),unowned_rotation_error_degrees=float(np.degrees(delta).max()),finite=bool(np.isfinite(b).all()))
        key=family+'/'+path.split('.')[-1];rows[key]=result
        if not result['finite'] or result['local_translation_error']>1e-7 or result['local_scale_error']>1e-7 or result['unowned_rotation_error_degrees']>1e-5:failures.append(key)
(root/'payload_review.json').write_text(json.dumps(dict(cases=rows,failures=failures),indent=2))
print('JOINT_ONLY_PAYLOAD',len(rows),'failures',failures)
if failures:raise RuntimeError('Joint-only contract failed')
