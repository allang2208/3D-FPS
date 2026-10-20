"""Scoped FK/skin regression for the requested magazine-placement repair."""
from arm_math import *
src=O.parent/'LeftReload20261019/scan_forearm_roll.py'
env={'__file__':str(src),'__name__':'magazine_contact_geometry'}
exec(compile(src.read_text(),str(src),'exec'),env)
new=json.loads((O/'profile_magazine_seat.json').read_text());report={'runtime_tested':False,'camera_source':'earlier accepted reload capture; offline projection only','clips':{}}
hi=ids['hand_l'];ui=ids['upperarm_l'];li=ids['lowerarm_l']
protected=[i for i,n in enumerate(names) if n.endswith('_r') or n.startswith('WPN_')]
for role in ('reload','reload_empty'):
    rows=[];maxbone=0.;maxprotected=0.;maxpalmangle=0.;aftercharge=0.;changedroot=[]
    c=motion['clips'][role]
    for i in range(len(c['times'])):
        a=pose(role,i);b=pose(role,i,new)
        maxprotected=max(maxprotected,float(abs(a[protected]-b[protected]).max()))
        for j,k in ((ui,li),(li,hi)):
            maxbone=max(maxbone,abs(np.linalg.norm(b[k,:3,3]-b[j,:3,3])-np.linalg.norm(a[k,:3,3]-a[j,:3,3])))
        maxpalmangle=max(maxpalmangle,float((R.from_matrix(rigid(a[hi])[:3,:3]).inv()*R.from_matrix(rigid(b[hi])[:3,:3])).magnitude()*180/np.pi))
        if role=='reload_empty' and i>=292:aftercharge=max(aftercharge,float(abs(a-b).max()))
        if i%4==0 and i<=304:
            cam=env['cam_at'](role,i);m0,_=env['visible_margin'](a,cam);m1,_=env['visible_margin'](b,cam)
            row={'frame':i,'root_before':int((m0<0).sum()),'root_after':int((m1<0).sum())};rows.append(row)
            if row['root_after']>row['root_before']:changedroot.append(row)
    report['clips'][role]={'max_bone_length_error_cm':float(maxbone),'max_right_and_mechanical_matrix_error':maxprotected,'max_palm_rotation_delta_deg':maxpalmangle,'left_charge_from_frame292_matrix_error':aftercharge,'increased_root_projection_samples':changedroot,'root_projection':rows}
    print(role,{k:v for k,v in report['clips'][role].items() if k!='root_projection'},flush=True)
(O/'contact_check.json').write_text(json.dumps(report,indent=2))
