"""Compare actual final graph before/after: elbow skin folds and unchanged main/finger contacts."""
from pathlib import Path
import sys
O=Path(__file__).parent
exec((O/'fit_elbow_helpers.py').read_text().split("frames=D['clips']")[0])
tag=sys.argv[1] if len(sys.argv)>1 else 'after'
before=json.loads((O/'graph_before.json').read_text());after=json.loads((O/f'graph_{tag}.json').read_text());report=[]
for old,new in zip(before['cases'],after['cases']):
    if old['case']=='post_off':continue
    assert (old['food'],old['case'])==(new['food'],new['case'])
    row={'food':old['food'],'case':old['case'],'elbow_folds_before':{},'elbow_folds_after':{},'max_contact_bone_position_change_cm':0.,'max_contact_bone_rotation_change_deg':0.}
    sides=['l','r'] if old['food']=='roasted_large_lamb' else ['l']
    for side in sides:
        cb=ca=0;times=[]
        for a,b in zip(old['samples'],new['samples']):
            if a['weight']<.01:continue
            wa=mat(np.array(a['world']));wb=mat(np.array(b['world']));v0=skin_metrics(wa,side)[0];v1=skin_metrics(wb,side)[0];cb=max(cb,v0);ca=max(ca,v1)
            if v1:times.append((a['time'],v1))
            for stem in ['upperarm','lowerarm','hand','thumb_01','thumb_02','thumb_03','index_03','middle_03','ring_03','pinky_03']:
                i=ix[stem+'_'+side];row['max_contact_bone_position_change_cm']=max(row['max_contact_bone_position_change_cm'],float(np.linalg.norm(wa[i,:3,3]-wb[i,:3,3])))
                row['max_contact_bone_rotation_change_deg']=max(row['max_contact_bone_rotation_change_deg'],float(np.rad2deg((Q.from_matrix(wa[i,:3,:3]).inv()*Q.from_matrix(wb[i,:3,:3])).magnitude())))
        row['elbow_folds_before'][side]=cb;row['elbow_folds_after'][side]=ca;row['remaining_'+side]=times
    report.append(row);print('FOOD_FINAL',row['food'],row['case'],row['elbow_folds_before'],'->',row['elbow_folds_after'],'contact delta',row['max_contact_bone_position_change_cm'],row['max_contact_bone_rotation_change_deg'],flush=True)
(O/('final_graph_comparison.json' if tag=='after' else f'final_graph_comparison_{tag}.json')).write_text(json.dumps(report,indent=2))
