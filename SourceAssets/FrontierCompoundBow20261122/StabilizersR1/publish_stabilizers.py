"""Publish the two Frontier options, three UI resources and the factory choice."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile

project,batch=[Path(x).resolve() for x in sys.argv[1:3]]
source=Path(__file__).resolve().parent
content=project/'Content'
catalog=content/'ColdSteelData/bow-gunsmith.json'
meshes='Weapons/FrontierCompoundBow/StabilizersR1'
icons='ColdSteelData/AttachmentIcons20260913/FramedBows'
weapon_id='bow_frontier_compound'
slot='stabilizer'
factory_icon=weapon_id+'_stabilizer_false'
factory='/Game/Weapons/FrontierCompoundBow/SM_Frontier_Stabilizer.SM_Frontier_Stabilizer'
specs=json.loads((source/'options.json').read_text(encoding='utf8'))
imports=json.loads((batch/'imported.json').read_text(encoding='utf8'))
if set(imports['meshes'])!=set(specs) or set(imports['icons'])!={factory_icon,*['stabilizer_'+key for key in specs]}:
    raise ValueError('Incomplete UE import')
def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(path,data,replace=False):
    if path.exists() and path.read_bytes()==data:return
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.frontier-staging',delete=False) as f:
        f.write(data)
        temp=Path(f.name)
    try:
        if replace:os.replace(temp,path)
        else:temp.rename(path)  # Windows does not replace an existing file on rename.
    finally:
        temp.unlink(missing_ok=True)

files={}
def install(rel,from_file):
    data=from_file.read_bytes()
    write(content/rel,data)
    files['Content/'+rel.as_posix()]=sha(data)

def package(path,name,folder):
    expected='/Game/'+folder+'/'+name+'.'+name
    if path!=expected:raise ValueError('Unexpected package '+path)
    base=batch/'Host/Content'/folder
    for file in [base/(name+'.uasset'),*[p for p in base.glob(name+'.*') if p.suffix in ('.uexp','.ubulk','.uptnl')]]:
        install(Path(folder)/file.name,file)

for key,spec in specs.items():package(imports['meshes'][key],spec['mesh'],meshes)
for name,path in imports['icons'].items():
    package(path,name,icons)
    install(Path(icons)/(name+'.png'),source/'Export/PartIcons'/(name+'.png'))

old=catalog.read_bytes()
body=old.decode('utf-8-sig')
eol='\r\n' if '\r\n' in body else '\n'
text=body.replace('\r\n','\n')
doc=json.loads(text)
weapon=next(w for w in doc['weapons'] if w['id']==weapon_id)
def fmt(value):
    return '\n    '.join(json.dumps(value,ensure_ascii=False,indent=2).splitlines())
def replace_once(text,needle,value):
    if text.count(needle)!=1:raise RuntimeError('Shared catalog layout changed')
    return text.replace(needle,value,1)

factory_visual={'bow_part_stabilizer_mesh':factory,'bow_part_stabilizer_scale':1,'bow_part_stabilizer_material':'',
                'bow_part_stabilizer_rods':0}
column={'key':slot,'name':'稳定杆','default':'原装稳定杆','description':'边境复合弓的原装前置稳定杆。',
        'factory_visual':{},'options':[]}
for key,spec in specs.items():
    visual={**factory_visual,'bow_part_stabilizer_mesh':imports['meshes'][key]}
    column['options'].append({'id':key,'name':spec['name'],'description':spec['description'],'appearance':spec['appearance'],
                              'weapons':[weapon_id],'visual':visual,'stats':spec['stats'],'special_effects':spec.get('special_effects',[])})

prior=next((c for c in doc['columns'] if c['key']==slot),None)
if prior and prior!=column:
    # Balance revisions own only the stats and effect copy of the existing Frontier options.
    updated=json.loads(json.dumps(prior))
    for option in updated['options']:
        if option['id'] in specs:
            spec=specs[option['id']]
            option.update(stats=spec['stats'],special_effects=spec.get('special_effects',[]))
    if updated!=column:raise RuntimeError('Another revision owns the stabilizer column')
    text=replace_once(text,fmt(prior),fmt(updated))
if not prior:
    last=fmt(doc['columns'][-1])
    text=replace_once(text,last,last+',\n    '+fmt(column))
before=fmt(weapon)
def scoped(mapping,key,value):
    if key in mapping and mapping[key]!=value:raise RuntimeError('Concurrent change to '+key)
    mapping[key]=value
for field in ('category_icon_sources','factory_icon_sources'):
    scoped(weapon[field],slot,factory_icon)
scoped(weapon['part_overrides'],slot,{'false':{'name':'原装稳定杆','description':'边境复合弓出厂配备的前置杆件。',
                  'appearance':'深色直杆前端带有宽环形端帽。','visual':factory_visual}})
text=replace_once(text,before,fmt(weapon))
bom=b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b''
new=bom+text.replace('\n',eol).encode('utf8')
backup=batch/'Before/bow-gunsmith.json'
if old!=new:
    if not backup.exists():write(backup,old)
    if catalog.read_bytes()!=old:raise RuntimeError('Catalog changed during publication. Rerun to merge.')
    write(catalog,new,True)
if not backup.exists():raise RuntimeError('No recorded preinstall configuration')
receipt={'weapon':weapon_id,'slot':slot,'factory':factory,'options':list(specs),'catalog':'Content/ColdSteelData/bow-gunsmith.json',
         'before_catalog':'Before/bow-gunsmith.json','before_catalog_sha256':sha(backup.read_bytes()),'after_catalog_sha256':sha(new),
         'files':files,'editable':str(source/'Frontier_Stabilizers.blend'),'runtime_tested':False}
native_files=['Source/FPSGAME/Weapons/Bow/BowGunsmith.cpp','Source/FPSGAME/UI/M4GunsmithLayout.cpp']
receipt['native_sources']={path:{'before':'Before/'+Path(path).name,
                                 'before_sha256':sha((batch/'Before'/Path(path).name).read_bytes()),
                                 'after_sha256':sha((project/path).read_bytes())} for path in native_files}
receipt['native_build_log']='build.log'
write(batch/'published.json',json.dumps(receipt,ensure_ascii=False,indent=2).encode('utf8'),True)
print('Published',len(specs),'stabilizers and',len(imports['icons']),'workbench icons.')
