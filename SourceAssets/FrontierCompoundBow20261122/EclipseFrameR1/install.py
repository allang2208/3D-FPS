"""Install only versioned Eclipse content and its Frontier-only riser entry."""
from pathlib import Path
import hashlib, json, os, sys, tempfile, shutil
root,batch=map(lambda x:Path(x).resolve(),sys.argv[1:3])
src=Path(__file__).resolve().parent
receipt=json.loads((batch/'imported.json').read_bytes())
paths=receipt['packages'];skin=paths['SK_Frontier_Eclipse']
icon='bow_frontier_compound_riser_frontier_eclipse'
expected={'M_Eclipse_Frame','T_Eclipse_Color','T_Eclipse_ORM','T_Eclipse_Normal','SK_Frontier_Eclipse',icon}
if set(paths)!=expected:raise ValueError('Incomplete import')
def sha(data):return hashlib.sha256(data).hexdigest()
def atomic(path,data,replace=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False,suffix='.eclipse-tmp') as f:
        f.write(data);temp=Path(f.name)
    try:
        if replace:os.replace(temp,path)
        elif path.is_file():
            if sha(path.read_bytes())!=sha(data):raise FileExistsError(path)
        else:temp.rename(path)
    finally:temp.unlink(missing_ok=True)
# Install dependency packages before registering the item.
files={}
for name,package in paths.items():
    base=Path('Content')/package.removeprefix('/Game/').split('.')[0]
    location=batch/'Host'/base
    package_file=location.with_suffix('.uasset')
    if not package_file.is_file():raise FileNotFoundError(package_file)
    for p in [package_file,*[s for s in location.parent.glob(name+'.*') if s.suffix in {'.uexp','.ubulk','.uptnl'}]]:
        files[base.parent/p.name]=p.read_bytes()
icon_file=Path('Content/ColdSteelData/AttachmentIcons20260913/FramedBows')/(icon+'.png')
files[icon_file]=(src/'Export'/icon_file.name).read_bytes()
for rel,data in files.items():atomic(root/rel,data)
catalog=root/'Content/ColdSteelData/bow-gunsmith.json'
orig=catalog.read_bytes();text=orig.decode('utf-8-sig')
doc=json.loads(text)
riser=next(c for c in doc['columns'] if c['key']=='riser')
option={'id':'frontier_eclipse','name':'蚀日弓体','weapons':['bow_frontier_compound'],
        'description':'边境复合弓专属传说弓体。','appearance':'石墨色弓架从握把上方收腰展开。拉丝古铜月牙嵌入上部眼形镂空，下弓架以一段短弧呼应。',
        'visual':{'bow_part_riser_mesh':skin,'bow_part_riser_material':'','bow_part_riser_scale':1},
        'stats':{},'special_effects':[]}
existing=next((o for o in riser['options'] if o['id']==option['id']),None)
before=batch/'Before/bow-gunsmith.json'
if existing is None:
    # Insert after the last object within this one column, retaining every other byte.
    last=riser['options'][-1]['id']
    marker=text.index('"id": "'+last+'"')
    start=text.rindex('{',0,marker)
    indent=text[text.rfind('\n',0,start)+1:start]
    end=start+json.JSONDecoder().raw_decode(text[start:])[1]
    eol='\r\n' if '\r\n' in text else '\n'
    serialized=eol.join(indent+line for line in json.dumps(option,ensure_ascii=False,indent=2).splitlines())
    updated=text[:end]+','+eol+serialized+text[end:]
    riser['options'].append(option)
    if json.loads(updated)!=doc:raise RuntimeError('Unexpected catalog delta')
    if not before.exists():atomic(before,orig)
    if catalog.read_bytes()!=orig:raise RuntimeError('Catalog advanced; rerun with the updated file.')
    atomic(catalog,(b'\xef\xbb\xbf' if orig.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf8'),True)
elif existing!=option:raise RuntimeError('Existing Eclipse option differs')
record={'revision':'EclipseFrameR1','weapon':'bow_frontier_compound','option':option,'tier':'Legendary',
    'skeleton':receipt['skeleton'],'material_slots':receipt['slots'],'packages':{r.as_posix():sha(d) for r,d in files.items()},
    'author':'SourceAssets/FrontierCompoundBow20261122/EclipseFrameR1/Frontier_Eclipse.blend',
    'catalog_before':'Before/bow-gunsmith.json','catalog_sha256':sha(catalog.read_bytes()),'runtime_tested':False}
rp=batch/'published.json'
if rp.exists() and 'build' in (old:=json.loads(rp.read_bytes())):record['build']=old['build']
atomic(rp,(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode(),True)
print('Published Eclipse',len(files),'files')
