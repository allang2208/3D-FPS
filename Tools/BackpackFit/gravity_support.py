"""Check that settled slings are supported by tethers/contact, not travel limits."""
import json,os
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
R=Path(os.environ['BACKPACK_FIT_RUN_DIR']);read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'plan.json');records=read(R/'captured.json');native=read(R/'native_contacts.json');result=[]
for row in plan['rows']:
    if 'hanging_pack' not in row:continue
    case=next(c for c in native['cases'] if c['rig'].lower()==row['rig'].lower() and c['item']==row['item'] and c['shirt']==row['shirt'])
    field=np.asarray(case['current_and_previous_wpo']);delta=field[3:12].reshape(3,3);bones={b['name']:b for b in records[row['body']]['bones']}
    moved=lambda p:p+(p-field[:3])@delta.T+field[12:15]
    recipe=row['hanging_pack'];slack=[]
    for tether in recipe['tethers']:
        anchor=np.zeros(3)
        for support in tether['support']:
            bone=bones[support['bone']];q=Rotation.from_quat(bone['rotation']).as_matrix()
            anchor+=(np.asarray(support['local'])@q.T+bone['position'])*support['weight']
        point=moved(np.asarray(tether['point']));slack.append(float(tether['length']-np.linalg.norm(point-anchor)))
    probes=moved(np.asarray(recipe['probes']));contacts=0;closest=np.inf
    for hull in recipe['hulls']:
        bone=bones[hull['bone']];q=Rotation.from_quat(bone['rotation']).as_matrix();local=(probes-bone['position'])@q
        planes=np.asarray(hull['planes']);dist=local@planes[:,:3].T+planes[:,3];sides=hull['side_planes']
        valid=np.all(dist[:,sides:]<.25,axis=1)
        if valid.any():
            side=dist[valid,:sides].max(1);contacts+=int(np.sum(side<=.25));closest=min(closest,float(side.min()))
    supported=min(slack)<.08 or contacts>0
    result.append({'rig':row['rig'],'shirt':row['shirt'],'tether_slack_cm':slack,'hull_contacts':contacts,'closest_hull_side_cm':closest,
                   'settled_translation_cm':float(np.linalg.norm(field[12:15])),'supported_by_tether_or_torso':bool(supported)})
report={'passed':all(r['supported_by_tether_or_torso'] for r in result),'rows':result,
        'scope':'Actual four-second settled native CPD pose and captured native binding frames; 0.08 cm tether and 0.05 cm contact-proxy tolerances'}
(R/'gravity_support.json').write_text(json.dumps(report,indent=2))
print('SLING_SUPPORT',report['passed'])
for row in result:print(row['rig'],row['shirt'] or 'bare','slack',*[round(v,3) for v in row['tether_slack_cm']],'contacts',row['hull_contacts'],'supported',row['supported_by_tether_or_torso'])
