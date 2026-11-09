"""Publish only M249's factory options; preserve concurrent unrelated catalogue edits."""
from pathlib import Path
import json,re,os,tempfile
root=Path(__file__).resolve().parents[1]
data=root.parents[1]/'Content/ColdSteelData'
parts=[('magazine','box','原厂弹箱'),('stock','stock','原厂枪托'),('reargrip','reargrip','原厂后握把'),
       ('underbarrel','foregrip','原厂前握把'),('muzzle','muzzle','原厂枪口'),('optic','magnifier','原厂后置倍镜')]
def replace(file,pattern,update):
    path=data/file;before=path.read_bytes();text=before.decode('utf-8-sig')
    matches=list(re.finditer(pattern,text))
    if not matches:raise RuntimeError('M249 entry missing in '+file)
    for match in reversed(matches):
        start=match.start('entry');original,count=json.JSONDecoder().raw_decode(text[start:])
        line=text[text.rfind('\n',0,start)+1:start];padding=len(line)-len(line.lstrip())
        replacement=json.dumps(update(original),ensure_ascii=False,indent=2).replace('\n','\n'+' '*padding)
        text=text[:start]+replacement+text[start+count:]
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as h:
        temp=Path(h.name);h.write(text.encode('utf-8-sig' if before.startswith(b'\xef\xbb\xbf') else 'utf8'))
    if path.read_bytes()!=before:temp.unlink();raise RuntimeError('Concurrent catalogue edit')
    os.replace(temp,path)
def factory(old):
    options={}
    for slot,part,label in parts:
        options[slot]=[dict(id='false',name=label,description='M249 原厂独立部件。',effects=[],stats={},special_effects=[],
                             factory_mesh=f'/Game/Weapons/M249/Assembly/SM_M249_{part}')]
    options['optic'][0]['description']='原厂后置倍镜独立安装；使用单一瞄具槽位。'
    old.update(inherit_common_options=False,allowed=[p[0] for p in parts],options=options)
    old.pop('default_parts',None)
    return old
if __name__=='__main__':
    replace('gunsmith.json',r'(?P<entry>\{\s*"id":\s*"ue_m249",)',factory)
    recipe=json.loads((root/'assembly.json').read_text(encoding='utf8'))
    replace('gun-assembly.json',r'(?P<entry>\{\s*"id":\s*"assemble_m249",)',lambda old:recipe)
    slots=json.loads((root/'assets_saved.json').read_text(encoding='utf8'))['skin_slots']
    replace('modular_outfits.json',r'"/Game/Weapons/M249/SK_M249_V7.SK_M249_V7":\s*(?P<entry>\{)',lambda old:{**old,'hide_source_materials':slots})
    print('M249_FACTORY_CATALOG',len(parts),'parts; skin slots',slots)
