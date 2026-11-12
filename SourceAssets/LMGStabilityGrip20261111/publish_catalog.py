"""Publish only this option, M249's bare default and its factory assembly recipe."""
from pathlib import Path
import json,re,os,tempfile
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1]
if not json.loads((HERE/'install_receipt.json').read_text())['complete']:raise RuntimeError('Asset save is required')
option=dict(id='lmg_stability_foregrip',name='机枪稳固握把',description='加宽防滑握面配合封闭式安装座，适配轻机枪下导轨，便于稳定托持和持续压枪。',
    effects=[dict(text='后坐力-15%',benefit=1),dict(text='枪械稳定性+15%',benefit=1)],
    stats=dict(recoil_mult=.85,stability_mult=1.15),special_effects=[
        '持续射击｜从首发起，额外加成随连续开火时间线性提高。1.5秒时，握把的后坐力减幅从15%提高至30%，枪械稳定性额外+15点。停火立即清零。',
        '轻机枪专属｜适用于 M249、201 和 PKM，占用前握把槽。'])
def write(path,transform):
    raw=path.read_bytes();text=raw.decode('utf-8-sig');changed=transform(text)
    backup=HERE/(path.name+'.before')
    if not backup.exists():backup.write_bytes(raw)
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent catalog write retained')
    path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+changed.encode('utf-8'))
def entry(text,id,fn):
    match=re.search(r'\{\s*"id"\s*:\s*"'+re.escape(id)+r'"\s*,',text)
    if not match:raise RuntimeError('Missing catalog entry '+id)
    start=match.start();old,count=json.JSONDecoder().raw_decode(text[start:]);fn(old)
    line=text[text.rfind('\n',0,start)+1:start];indent=len(line)-len(line.lstrip());newline='\r\n' if '\r\n' in text[start:start+count] else '\n'
    replacement=json.dumps(old,ensure_ascii=False,indent=2).replace('\n','\n'+' '*indent).replace('\n',newline)
    return text[:start]+replacement+text[start+count:]
def catalog(text):
    def bare(w):
        o=next(o for o in w['options']['underbarrel'] if o['id']=='false')
        o.update(name='无前握把',description='不安装前握把，左手托持原厂护木。',effects=[],stats={},special_effects=[]);o.pop('factory_mesh',None)
        if 'default_parts' in w:w['default_parts'].pop('underbarrel',None)
    text=entry(text,'ue_m249',bare)
    # Shared class catalog is authoritative; no per-weapon stat copies.
    data=json.loads(text)
    value=data.get('lmg_options',{})
    grips=value.setdefault('underbarrel',[])
    for i,grip in enumerate(grips):
        if grip['id']==option['id']:
            grips[i]=option
            break
    else:
        grips.append(option)
    if 'lmg_options' in data:
        m=re.search(r'"lmg_options"\s*:',text);start=m.end()
        while text[start].isspace():start+=1
        current,count=json.JSONDecoder().raw_decode(text[start:])
        if current!=value:
            text=text[:start]+json.dumps(value,ensure_ascii=False,indent=2)+text[start+count:]
    else:
        end=text.rfind('}');text=text[:end].rstrip()+',\n  "lmg_options": '+json.dumps(value,ensure_ascii=False,indent=2).replace('\n','\n  ')+'\n'+text[end:]
    return text
write(PROJECT/'Content/ColdSteelData/gunsmith.json',catalog)
write(PROJECT/'Content/ColdSteelData/gun-assembly.json',lambda text:entry(text,'assemble_m249',lambda r:r.update(parts=[p for p in r['parts'] if p['id']!='foregrip'])))
write(HERE.parent/'M249Orpind20261107/assembly.json',lambda text:entry(text,'assemble_m249',lambda r:r.update(parts=[p for p in r['parts'] if p['id']!='foregrip'])))
(HERE/'catalog_receipt.json').write_text(json.dumps(dict(option=option,compatible=['ue_m249','ue_lmg201','ue_pkm_lowpoly'],old_empty_loadouts='remain empty; no implicit free upgrade',runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('Shared LMG option and bare M249 factory recipe published.')
