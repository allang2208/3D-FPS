"""Install this revision against known predecessor hashes without overwriting concurrent catalog edits."""
from pathlib import Path
import json,hashlib,tempfile,os,shutil,sys,datetime
source=Path(__file__).resolve().parent
project,batch,review=map(Path,sys.argv[1:4])
old=batch.parent/'Initial20261122'
load=lambda p:json.loads(p.read_bytes().decode('utf-8-sig'))
sha=lambda b:hashlib.sha256(b).hexdigest()
state=load(batch/'editor-state.json')
if state['dirty']:raise RuntimeError('Preserve unsaved bow packages: '+str(state))
samples=load(review/'mesh-contact.json')
if len(samples)!=25 or any(s['strand_hits'] or s['shaft_hits'] for s in samples):
    raise RuntimeError('Resolve unexpected contact in the draw sweep')
raws={};outputs={};manifest={}
def stage(path,blob):
    before=path.read_bytes() if path.exists() else None
    if blob!=before:raws[path]=before;outputs[path]=blob
def unpack(file):
    text=file.read_bytes().decode('utf-8-sig')
    return text,'\r\n' if '\r\n' in text else '\n'
def patch_record(filename,section,change):
    file=project/'Content/ColdSteelData'/filename
    text,eol=unpack(file);original=text.replace('\r\n','\n')
    document=json.loads(text);wid='bow_frontier_compound'
    if section:
        row=next(x for x in document[section] if x['id']==wid);indent=4
    else:
        row=document[wid];indent=2
    def fmt(obj):
        return ('\n'+' '*indent).join(json.dumps(obj,ensure_ascii=False,indent=2).splitlines())
    before=fmt(row);change(row);after=fmt(row)
    if original.count(before)!=1:raise RuntimeError('Unrecognized catalog layout '+filename)
    body=original.replace(before,after).replace('\n',eol)
    assert json.loads(body)==document
    bom=b'\xef\xbb\xbf' if file.read_bytes().startswith(b'\xef\xbb\xbf') else b''
    stage(file,bom+body.encode('utf8'))
packages={**load(batch/'import.json'),**load(batch/'icons.json')}
for obj in packages.values():
    leaf=Path(obj.split('.')[0].removeprefix('/Game/')+'.uasset')
    staged=batch/'Host/Content'/leaf
    paths=[(leaf,staged)]
    if leaf.parts[0]=='ColdSteelData':
        if not leaf.stem.endswith('_r2'):raise ValueError(obj)
        original=leaf.stem.removesuffix('_r2')+'.png'
        png=source/'Export'/original if leaf.parent.name=='Icons' else source/'Export/PartIcons'/original
        paths.append((leaf.with_suffix('.png'),png))
    elif 'RigContactR2' not in leaf.parts:raise ValueError(obj)
    for rel,src in paths:
        path=project/'Content'/rel
        blob=src.read_bytes()
        if path.exists() and sha(path.read_bytes())!=sha(blob):
            raise RuntimeError('Unrecognized production revision '+str(rel))
        stage(path,blob)
anchors=load(source/'anchors.json')
def vector(v):return ','.join(f'{k:.5f}'.rstrip('0').rstrip('.') if abs(k)>.000001 else '0' for k in v)
def set_bow(row):
    row.update(bow_presentation_revision=35,bow_part_riser_mesh=packages['SK_Frontier_Assembly'],
        bow_part_arrow_rest_mesh=packages['SM_Frontier_Rest'],ue_icon='Icons/bow_frontier_compound_r2.png')
    for a,k in [('upper','nock_upper_cm'),('lower','nock_lower_cm'),('brace','brace_nock_cm'),('draw','draw_anchor_cm'),('rest','arrow_rest_cm')]:
        row[k]=vector(anchors[a])
def set_gunsmith(row):
    for option in row['part_overrides']['riser'].values():
        option['visual']['bow_part_riser_mesh']=packages['SK_Frontier_Assembly']
    for option in row['part_overrides']['arrow_rest'].values():
        option['visual']['arrow_rest_cm']=vector(anchors['rest'])
        option['visual']['bow_part_arrow_rest_mesh']=packages['SM_Frontier_Rest']
    for slot in ('riser','arrow_rest'):
        for mapping in ('category_icon_sources','factory_icon_sources'):
            row[mapping][slot]='bow_frontier_compound_'+slot+'_false_r2'
    # Physical optional optics retain their own lens/mount alignment.
    row['part_overrides']['arrow_rest']['false']['description']='侧装座向持弓手一侧伸出独立托槽，托住就位的箭杆。'
patch_record('bows.json',None,set_bow)
patch_record('bow-gunsmith.json','weapons',set_gunsmith)
ini=project/'Config/DefaultEngine.ini'
text,eol=unpack(ini)
header='[CoreRedirects]'
if text.count(header)!=1:raise RuntimeError('Missing redirect section')
redirects=[]
for name in ('SK_Frontier_Assembly','SK_Frontier_Assembly_Skeleton','SM_Frontier_Rest'):
    new=packages[name].split('.')[0];old_path=new.replace('/RigContactR2/','/')
    redirects.append('+PackageRedirects=(OldName="'+old_path+'",NewName="'+new+'")')
added=[line for line in redirects if line not in text.splitlines()]
if added:
    raw=ini.read_bytes()
    stage(ini,(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+
          text.replace(header,header+eol+eol.join(added),1).encode('utf8'))
when=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
backup=batch/'Before'/when
for p,blob in raws.items():
    if blob is None:continue
    target=backup/p.relative_to(project);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
def swap(path,data):
    with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.frontier-install',delete=False) as f:
        f.write(data);tmp=Path(f.name)
    try:os.replace(tmp,path)
    finally:tmp.unlink(missing_ok=True)
changed=[]
try:
    for p,data in outputs.items():
        if (p.read_bytes() if p.exists() else None)!=raws[p]:raise RuntimeError('Concurrent edit '+str(p))
        p.parent.mkdir(parents=True,exist_ok=True)
        swap(p,data);changed.append(p)
except Exception:
    for p in reversed(changed):
        if p.read_bytes()==outputs[p]:
            if raws[p] is None:p.unlink()
            else:swap(p,raws[p])
    raise
for p in changed:
    if p.read_bytes()!=outputs[p]:raise RuntimeError('Installed bytes differ '+str(p))
    manifest[p.relative_to(project).as_posix()]={'before':sha(raws[p]) if raws[p] is not None else None,'after':sha(outputs[p])}
receipt=batch/'published.json'
if changed or not receipt.exists():
    receipt.write_text(json.dumps({'revision':'RigContactR2','files':manifest,'before':str(backup),'source':str(source),
        'comparison':str(review),'editor_and_game_build':['editor-build.log','game-build.log']},ensure_ascii=False,indent=2),encoding='utf8')
print('Installed',len(changed),'files.')
