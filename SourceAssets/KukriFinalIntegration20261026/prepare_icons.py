"""Record the actual Kukri menu inputs and stable runtime destinations for this batch."""
import json, shutil, hashlib
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
DATA=ROOT/'Content/ColdSteelData'
ICONS=DATA/'AttachmentIcons20260913'
FRAME=ROOT/'SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png'
for folder in ('Inputs','Generated','Before','Receipts'):(P/folder).mkdir(exist_ok=True)
menu=json.loads((DATA/'kukri-gunsmith.json').read_text(encoding='utf-8-sig'))
assembly=json.loads((DATA/'kukri-modules.json').read_text(encoding='utf-8-sig'))
manifest={'weapon':'ue_kukri','frame_reference':str(FRAME),'masters':[],'bindings':[],
          'rendering':'imagegen from current model render plus approved metal frame',
          'numeric_changes':False,'runtime_tested':False}
factory=ROOT/'SourceAssets/KukriModules20261026'
for col in menu['columns']:
    slot=col['key']
    options=list(col.get('options',[]))
    if col.get('options_library'):
        lib=json.loads((DATA/col['options_library']).read_text(encoding='utf-8-sig'))
        options+=lib.get('options',[]) if not col.get('options_column') else next(c['options'] for c in lib['columns'] if c['key']==col['options_column'])
    for opt in [{'id':'false','name':col['default']}]+options:
        oid=opt['id'];key=f'{slot}_{oid}'
        runtime_key=f'ue_kukri_{key}' if oid in ('false','no_lanyard') else key
        if oid in ('false','no_lanyard'):
            if slot=='blade_2' or oid=='no_lanyard':master='remove';source=factory/'Icons/blade_2.png';generate=False
            else:
                master=runtime_key;generate=slot in ('grip','pommel')
                name={'blade_1':'Blade','grip':'Grip','pommel':'Pommel','lanyard':'Lanyard'}[slot]
                source=factory/'IconInputs'/f'SM_Kukri_{name}_Factory.png' if generate else factory/'Icons'/f'{slot}.png'
        else:
            master=key;generate=True
            batch='KukriBladeVariants20261026' if slot=='blade_1' else 'KukriComponentVariants20261026'
            source=ROOT/'SourceAssets'/batch/'Icons'/f'{key}.png'
        if not any(m['id']==master for m in manifest['masters']):
            copied=P/'Inputs'/f'{master}.png';shutil.copy2(source,copied)
            spec=assembly['slots'][slot].get('factory' if oid=='false' else oid,{})
            manifest['masters'].append({'id':master,'name':opt['name'],'slot':slot,'source':str(source),
                'input':str(copied),'generate':generate,'runtime_mesh':spec.get('mesh'),
                'surface_materials':spec.get('surface_materials',{}),'output':str(P/'Generated'/f'{master}.png') if generate else str(copied)})
        manifest['bindings'].append({'key':runtime_key,'master':master,'kind':'option','slot':slot,'option':oid})
    category_master='blade_2_knife_mark_wing' if slot=='blade_2' else f'ue_kukri_{slot}_false'
    manifest['bindings'].append({'key':f'ue_kukri_category_{slot}','master':category_master,'kind':'category','slot':slot})
for job in manifest['bindings']:
    target=ICONS/(job['key']+'.png')
    job['runtime_png']=str(target);job['texture']='/Game/ColdSteelData/AttachmentIcons20260913/'+job['key']
    if target.exists():
        shutil.copy2(target,P/'Before'/target.name)
        job['before_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
(P/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(f"Prepared {len(manifest['masters'])} masters, {sum(m['generate'] for m in manifest['masters'])} imagegen jobs, {len(manifest['bindings'])} menu bindings")
