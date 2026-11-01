"""Compare newly reloaded UE values with the pre-change sources and save receipt."""
import json
from pathlib import Path
O=Path(__file__).resolve().parent
old=json.loads((O.parent/'inputs.json').read_text(encoding='utf-8'))
live=json.loads((O/'inputs.json').read_text(encoding='utf-8'))
published=json.loads((O.parent/'install_receipt.json').read_text(encoding='utf-8'))
project=O.parents[2]
catalog=json.loads((project/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8'))
weapon=next(w for w in catalog['weapons'] if w['id']=='ue_m24')
result={'binding_matches':True,'rows':[],'stock_options':weapon['options']['stock'],
        'default_stock':weapon['default_parts']['stock'],'inherit_common_options':weapon.get('inherit_common_options',True),
        'legacy_stock_resolution':'Source Normalize drops absent stock/none and fills default_parts.stock',
        'visual_acceptance':False}
for key,row in live['assets'].items():
    expected={r['slot']:r for r in published['bindings'][row['path']]}
    for i,slot in enumerate(row['slots']):
        source=old['assets'][key]['slots'][i]['material']
        previous=old['materials'][source]['parameters']
        now=live['materials'][slot['material']]['parameters']
        matches=slot['material']==expected[slot['slot']]['material']
        result['binding_matches'] &= matches
        changes={p:{'before':previous['scalar'].get(p),'after':now['scalar'].get(p)}
                 for p in ('Metallic','Roughness','ContinuityNormalStrength','SourceRoughnessWeight','EdgeHighlight','GrainRoughness','MaskUVChannel','RainSurfaceResponse')
                 if previous['scalar'].get(p)!=now['scalar'].get(p)}
        result['rows'].append({'assembly':key,'slot':slot['slot'],'binding_matches':matches,'changes':changes,
                               'normal_preserved':previous['texture'].get('SurfaceNormal')==now['texture'].get('SurfaceNormal'),
                               'mask_preserved':previous['texture'].get('SurfaceMask')==now['texture'].get('SurfaceMask')})
result['stock_ok']=(not result['inherit_common_options'] and {x['id'] for x in result['stock_options']}=={'m24_cheekrest','sniper_skeleton_stock'}
                    and result['default_stock']=='m24_cheekrest')
finish_rows=[r for p,r in live['materials'].items() if '/StockMetalFinish20261031/' in p]
result['recognized_parent_count']=sum(r['master'].split('.')[0]=='/Game/Weapons/M24/AdvancedAction20261029/Materials/M_M24AdvancedSurface' for r in finish_rows)
result['wet_response_ok']=all(abs(r['parameters']['scalar']['RainSurfaceResponse']-(1 if r['parameters']['scalar']['Metallic']>.5 else 2))<1e-6 for r in finish_rows)
result['visual_findings']={
    'verdict':'Material edits are saved and visible, but reference-level surface quality is not achieved',
    'evidence':'Native/*.png uses saved UE materials and identical studio lighting; NormalProbe/*.png replaces SurfaceNormal transiently',
    'original_stock_branch':'Slightly darker satin finish; improvement is modest',
    'skeleton_branch':'Narrower highlights, but ribbed receiver reflections and uneven handguard highlights persist',
    'normal_probe':'Flat SurfaceNormal does not remove the broad shading defects; mesh smoothing/triangulation is the leading remaining cause',
    'not_completed':'Mesh corner-normal/triangulation repair and in-game appearance acceptance',
    'geometry_changed_in_this_review':False,
    'gameplay_test':False,
}
(O/'comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'bindings_match':result['binding_matches'],'slots':len(result['rows']),'stock_ok':result['stock_ok'],
                  'changed_slots':sum(bool(r['changes']) for r in result['rows'])}))
