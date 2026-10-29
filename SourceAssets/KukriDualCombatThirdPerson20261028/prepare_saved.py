"""Use saved authoring sources whose receipts still match the active roles."""
import hashlib,json
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
native=json.loads((ROOT/'SourceAssets/KukriWhirlwindSourceMotion20261025/active-inputs.json').read_text())
folders={'Dual.Idle':'KukriDualIdleThirdPerson20261027','Slash1':'KukriThirdPerson20261024/ComboV3',
    'Slash2':'KukriThirdPerson20261024/ComboV3','Thrust':'KukriThrustSourceArm20261025','Charge':'KukriHeavy20261025','Heavy':'KukriHeavy20261025'}
result={}
for label in ('jason','kaitlin'):
    active=cfg if label=='jason' else cfg['body_variants'][label]
    entry=dict(native=native[label],clips={},previous_roles={r:active['clips'].get('Kukri.FullBody.Dual.'+r) for r in ('Slash1','Slash2','Thrust','Charge','Heavy','Recover1','Recover2')})
    for role,folder in folders.items():
        path=ROOT/'SourceAssets'/folder;receipt=json.loads((path/'assets-saved.json').read_text())['bodies'][label]
        raw=(path/(label+'-actions.json')).read_bytes();data=json.loads(raw);key='Kukri.FullBody.'+role
        expected=receipt.get('source_sha256') or receipt['source_hashes'][key]
        if hashlib.sha256(raw).hexdigest()!=expected or active['clips'][key]!=receipt['clips'][key]:raise RuntimeError('Saved source changed: '+key)
        if data['mesh']!=active['body_mesh'] or data['names']!=native[label]['names']:raise RuntimeError('Native body changed')
        clip=data['clips'][role];rate=clip['rate_num']/clip['rate_den'] if 'rate_num' in clip else clip['rate'];duration=(len(clip['frames'])-1)/rate
        entry['clips'][role]=dict(asset=receipt['clips'][key],duration=duration,rate=rate,frames=clip['frames'],
            markers={'Contact':clip['contact']*duration,'Release':clip['release']*duration},source_sha256=expected)
    result[label]=entry
(OUT/'inputs.json').write_text(json.dumps(result,separators=(',',':')))
print('DUAL_COMBAT_SAVED_SOURCES_PREPARED')
