import json,re
from pathlib import Path
p=Path(__file__).parent
def values(text):
    m=re.search(r'PropertyValues=("(?:[^"\\]|\\.)*")',text)
    return json.loads(json.loads(m[1])) if m else {'export':text[:450]}
r=json.loads((p/'inspection.json').read_text(encoding='utf-8'))
for name,e in r['emitters'].items():
    d=values(e['data']);v=values(e['renderer'])
    print(name,json.dumps({'data':d,'renderer':{k:x for k,x in v.items() if not isinstance(x,dict) or 'Binding' in k and k in ['DynamicMaterialBinding','ColorBinding','PositionBinding','SpriteSizeBinding','RendererVisibilityTagBinding']},'modules':re.findall(r'ModuleName="([^"]+)"',e['topology'])}))
print('SYSTEM',r['summary'][:3200])
src=json.loads((p.parent/'source-topology.json').read_text(encoding='utf-8'))
print('SOURCE_KEYS',list(src))
for name,e in src.items():
    if isinstance(e,dict):
        print('SOURCE_EMITTER',name)
        for k,v in e.items():
            if isinstance(v,list):print(k,[re.findall(r'ModuleName="([^"]+)"',x) for x in v if isinstance(x,str)])
