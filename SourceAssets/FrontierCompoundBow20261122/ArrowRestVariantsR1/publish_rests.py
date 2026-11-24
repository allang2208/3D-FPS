"""Publish the three saved packages and switch the Frontier rest options as one catalog edit."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile

project,batch = (Path(arg).resolve() for arg in sys.argv[1:3])
source = Path(__file__).resolve().parent
catalog = project/'Content/ColdSteelData/bow-gunsmith.json'
rest_dir = 'Weapons/FrontierCompoundBow/ArrowRestVariantsR1'
factory = '/Game/Weapons/FrontierCompoundBow/RigContactR2/SM_Frontier_Rest.SM_Frontier_Rest'
rests = json.loads((source/'rests.json').read_text(encoding='utf8'))
imports = json.loads((batch/'imported.json').read_text(encoding='utf8'))
receipt = batch/'published.json'
previous = json.loads(receipt.read_text(encoding='utf8')) if receipt.exists() else {}
digest = lambda b: hashlib.sha256(b).hexdigest()

def stage(path, data, replace):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False,suffix='.frontier-install') as f:
        f.write(data)
        tmp=Path(f.name)
    try:
        if replace:
            os.replace(tmp,path)
        else:
            try:
                tmp.rename(path)  # Windows refuses to overwrite an existing target.
            except FileExistsError:
                if path.read_bytes()!=data:
                    raise RuntimeError('Versioned file already contains a different revision: '+str(path))
    finally:
        tmp.unlink(missing_ok=True)

if set(rests)!=set(imports['meshes']):
    raise ValueError('Incomplete import receipt')
packages = {}
for key,row in rests.items():
    name = row['mesh']
    package = '/Game/'+rest_dir+'/'+name+'.'+name
    if imports['meshes'][key]!=package:
        raise ValueError('Unexpected imported package '+key)
    location = batch/'Host/Content'/rest_dir
    for file in [location/(name+'.uasset'), *[p for p in location.glob(name+'.*') if p.suffix in ('.uexp','.ubulk','.uptnl')]]:
        data = file.read_bytes()
        target = project/'Content'/rest_dir/file.name
        stage(target,data,False)
        packages[target.relative_to(project).as_posix()] = digest(data)

old = catalog.read_bytes()
body = old.decode('utf-8-sig')
eol = '\r\n' if '\r\n' in body else '\n'
text = body.replace('\r\n','\n')
doc = json.loads(text)
weapon = next(w for w in doc['weapons'] if w['id']=='bow_frontier_compound')
slots = weapon['part_overrides']['arrow_rest']
def formatted(obj):
    return '\n    '.join(json.dumps(obj,ensure_ascii=False,indent=2).splitlines())

before = formatted(weapon)
for key,design in rests.items():
    slot=slots[key]
    mesh=imports['meshes'][key]
    if slot['visual']['bow_part_arrow_rest_mesh'] not in (factory,mesh):
        raise ValueError('Another revision owns the active '+key+' option')
    slot['visual']['bow_part_arrow_rest_mesh']=mesh
    for field in ('name','description','appearance'):
        slot[field]=design[field]
if text.count(before)!=1:
    raise RuntimeError('Unexpected catalog formatting')
bom = b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b''
new = bom + text.replace(before,formatted(weapon),1).replace('\n',eol).encode('utf8')
backup=batch/'Before/bow-gunsmith.json'
if old!=new:
    if not backup.exists():
        stage(backup,old,False)
    if catalog.read_bytes()!=old:
        raise RuntimeError('Catalog changed during installation. Rerun against the current file.')
    stage(catalog,new,True)
if not backup.exists():
    raise RuntimeError('Missing pre-install catalog')
# The rollback fields remain scoped even if other items in the shared catalog subsequently change.
backup_doc=json.loads(backup.read_bytes().decode('utf-8-sig'))
backup_slots=next(row for row in backup_doc['weapons'] if row['id']==weapon['id'])['part_overrides']['arrow_rest']
record={'weapon':weapon['id'],'slot':'arrow_rest','packages':packages,
        'catalog':catalog.relative_to(project).as_posix(),'before_snapshot':'Before/bow-gunsmith.json',
        'before_catalog_sha256':digest(backup.read_bytes()),'catalog_sha256':digest(new),
        'before_options':{key:backup_slots[key] for key in rests},
        'after_options':{key:slots[key] for key in rests},'editable':str(source/'Frontier_ArrowRests.blend'),
        'runtime_tested':False}
if not previous or old!=new:
    stage(receipt,json.dumps(record,ensure_ascii=False,indent=2).encode('utf8'),True)
print('Published',len(rests),'Frontier rest options;',len(packages),'package files.')
