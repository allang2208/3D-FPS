import re,json
from pathlib import Path
out=Path(__file__).parent
def parse(file):
    objects={};stack=[]
    for line in file.read_text(encoding='utf-8-sig').splitlines():
        line=line.strip()
        if line.startswith('Begin Object'):
            path=re.search(r"ExportPath=\"([^']+)'([^']+)'",line)
            if not path:raise ValueError(line)
            cls,key=path.groups();node=objects.setdefault(key,{'class':cls.rsplit('.',1)[-1],'props':{},'children':[]})
            if stack and key not in stack[-1]['children']:stack[-1]['children'].append(key)
            stack.append(node)
        elif line=='End Object':stack.pop()
        elif stack and '=' in line:
            key,value=line.split('=',1);stack[-1]['props'][key]=value
    root=next(k for k,v in objects.items() if v['class']=='ParticleSystem')
    def get(value,owner=root):
        name=re.search("'([^']+)'",value).group(1)
        if name.startswith('/Game/'):key=name
        elif ':' in name:key=root+':'+name.split(':',1)[1]
        else:key=owner+('.' if ':' in owner else ':')+name
        return key,objects[key]
    rows=[];seen=set()
    for k,value in objects[root]['props'].items():
        if not k.startswith('Emitters('):continue
        ek,e=get(value);lk,l=get(e['props']['LODLevels(0)'],ek)
        _,req=get(l['props']['RequiredModule']);mat=req['props'].get('Material','')
        if not any(x in mat for x in ['M_Fire_','M_Explosion_','M_Smoke_']):continue
        if mat in seen:continue
        seen.add(mat)
        row={'emitter':e['props'].get('EmitterName'),'required':req['props'],'modules':[]}
        for mk,mv in l['props'].items():
            if not(mk.startswith('Modules(') or mk=='SpawnModule'):continue
            key,m=get(mv)
            if any(x in m['class'] for x in ['Color','SubUV','Lifetime','Dynamic','Spawn','Velocity','Size']):
                row['modules'].append({'class':m['class'],'props':{a:b[:850] for a,b in m['props'].items() if not a.startswith(('ModuleEditor','LOD','bSpawn','bUpdate'))},'distributions':[{'class':objects[c]['class'],'props':{a:b[:900] for a,b in objects[c]['props'].items()}} for c in m['children']]})
        rows.append(row)
    return rows
profiles={p.stem:parse(p) for p in out.glob('*.t3d')}
(out/'cascade-profiles.json').write_text(json.dumps(profiles,indent=2),encoding='utf8')
for name,rows in profiles.items():
    print(name)
    for row in rows:
        print(row['emitter'],{k:v for k,v in row['required'].items() if k in ['Material','SubImages_Horizontal','SubImages_Vertical']})
        for m in row['modules']:
            if any(x in m['class'] for x in ['SubUV','Color','Dynamic']):print(json.dumps(m))
