"""Compare existing loader authoring with a root-basis correction in memory.

Research only: no source edits, animation baking, export, UE import or render.
"""
import json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
path=O.parent/'Super90Speedloader20261007/author_speedloader.py'
code=path.read_text(encoding='utf-8-sig').split('def local_rows(world):')[0]
root_fix="""
eval_base={}
for n in names:
    eval_base[n]=eval_base.get(parents[n],I)@uemat(D['clips']['idle']['samples'][0]['local'][n])
root=next(n for n in names if parents[n] is None)
evaluation_to_author=idle[root]@(Ci@eval_base[root]@Ki[root]).inverted()
"""
fixed=code.replace("idles={'base':idle}",root_fix+"\nidles={'base':idle}")
fixed=fixed.replace('n:Ci@world[n]@Ki[n]','n:evaluation_to_author@Ci@world[n]@Ki[n]')
report={'scope':'in-memory research comparison; no production edit or export','versions':{}}
for label,source in [('current',code),('root_basis_only',fixed)]:
    s={'__file__':str(path)};exec(compile(source,str(path),'exec'),s)
    h=s['hand_in_handle'];binding=s['rest']['hand_l']@h.inverted()
    result={'hand_in_handle_offset_cm':[v*100 for v in h.translation],
            'hand_in_handle_scale':list(h.to_scale()),'plunger_bind_scale':list(binding.to_scale()),'poses':[]}
    for family in ('base','vertical'):
        for f in (0,23,56,75,87,90,114,127,140,146):
            pose,handle,tube=s['pose'](f,7,False,family)
            result['poses'].append({'family':family,'frame':f,'real_seconds':f/78.,
                'hand_scale':list(pose['hand_l'].to_scale()),'lowerarm_scale':list(pose['lowerarm_l'].to_scale()),
                'wrist_to_handle_origin_cm':(pose['hand_l'].translation-handle.translation).length*100,
                'hand_position':list(pose['hand_l'].translation)})
    report['versions'][label]=result
(O/'loader_contact_study.json').write_text(json.dumps(report,indent=2))
print('LOADER_CONTACT_STUDY',json.dumps({k:{'offset_cm':v['hand_in_handle_offset_cm'],'scale':v['hand_in_handle_scale'],'prop_bind_scale':v['plunger_bind_scale'],
    'at_dock':[p for p in v['poses'] if p['family']=='base' and p['frame']==87][0]} for k,v in report['versions'].items()}),flush=True)
