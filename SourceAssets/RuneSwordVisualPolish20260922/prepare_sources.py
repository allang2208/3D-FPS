"""Freeze the requested icon set and preserve the exact files being replaced."""
from pathlib import Path
import json, shutil, hashlib

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
CAT=ROOT/'Content/ColdSteelData'
ICONS=CAT/'AttachmentIcons20260913'
BEFORE=P/'Before'; BEFORE.mkdir(exist_ok=True)
catalog=json.loads((CAT/'melee-gunsmith.json').read_text(encoding='utf-8-sig'))
modules=json.loads((CAT/'rune-sword-modules.json').read_text(encoding='utf-8-sig'))
shared=json.loads((CAT/'shared-sword-pommels.json').read_text(encoding='utf-8-sig'))
rows=[]
for col in catalog['columns']:
    slot=col['key']
    for option in [{'id':'false','name':col['default']}]+col.get('options',[]):
        if option.get('weapons') and 'ue_rune_sword' not in option['weapons']:continue
        key=option['id']; spec=modules['slots'].get(slot,{}).get('factory' if key=='false' else key)
        if slot=='pommel' and key in shared['options']:
            spec=dict(shared['options'][key])
            spec.update(modules['pommel_profile']['interfaces'][spec['interface']])
            spec.update(shared['finishes']['silver'].get(key,{}))
        if not spec:spec=modules['slots']['blade_1' if slot=='blade_2' else slot]['factory']
        rows.append({'slot':slot,'id':key,'name':option['name'],'key':'ue_rune_sword_'+slot+'_'+key,
            'spec':spec,'numeric_only':slot=='blade_1' and key!='false'})
    rows.append({'slot':slot,'id':'category','key':'ue_rune_sword_category_'+slot,'copy':'ue_rune_sword_'+slot+'_false'})
(P/'icon_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
baseline=[]
for row in rows:
    for ext in ['.png','.uasset']:
        src=ICONS/(row['key']+ext)
        if src.exists():
            dst=BEFORE/src.name
            if not dst.exists():shutil.copy2(src,dst)
            baseline.append({'path':str(src),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'bytes':dst.stat().st_size})
for name in ['T_RuneSword_NativeMask.png','native_ink_mask.png','blade_uv_source.npz','authoring.json','bake_native_mask.py']:
    src=P.parent/'NativeRuneGold20260922'/name
    dst=BEFORE/name
    if not dst.exists():shutil.copy2(src,dst)
(P/'baseline.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2),encoding='utf-8')
print('ICON_SOURCES_PREPARED',len(rows),'icons')
