"""Publish the two revised cosmetic meshes and switch their existing inventory choices in place."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile

src=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False,suffix='.framefit-tmp') as f:
        f.write(data);tmp=Path(f.name)
    try:os.replace(tmp,path)
    finally:tmp.unlink(missing_ok=True)
def install(root,batch,editor=None):
    root=root.resolve()
    if not (root/'FPSGAME.uproject').is_file():raise RuntimeError('FPSGAME project required')
    if editor and Path(editor.Paths.convert_relative_path_to_full(editor.Paths.get_project_file_path())).resolve().parent!=root:
        raise RuntimeError('Unexpected live editor project')
    def closed():
        line=subprocess.check_output(['tasklist','/fi','imagename eq UnrealEditor.exe','/fo','csv','/nh'],encoding='mbcs',errors='replace')
        return '"unrealeditor.exe"' not in line.lower()
    imported=json.loads((batch/'imported.json').read_bytes())
    before=batch/'Before';writes=[];record={}
    cat=Path('Content/ColdSteelData/bow-gunsmith.json')
    old=(root/cat).read_bytes();new=old
    doc=json.loads(old.decode('utf-8-sig'))
    opts=next(x['options'] for x in doc['columns'] if x['key']=='riser')
    for kind,previous in [('Eclipse','CamLinesR11'),('Aurora','AuroraFrameR1')]:
        e=imported[kind]
        icon='bow_frontier_compound_riser_frontier_'+kind.lower()
        name='SK_Frontier_'+kind
        if sha((src/'Export'/(name+'.fbx')).read_bytes())!=e['fbx_sha256'] or sha((src/'Export'/(icon+'.png')).read_bytes())!=e['png_sha256']:
            raise RuntimeError('Import is not from final sources: '+kind)
        history=json.loads((batch.parent/(kind+'FrameR1_20261123')/'published.json').read_bytes())
        previous_hashes=history.get('package_sha256',history.get('packages'))
        for key in ('mesh','icon'):
            package=e[key].split('.')[0]
            entry=Path('Content')/package.removeprefix('/Game/')
            if editor and editor.find_object(None,e[key]):raise RuntimeError('Target package in use: '+e[key])
            if editor and any(p.get_name()==package for p in editor.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
                raise RuntimeError('Unsaved package: '+package)
            for f in (batch/'Host'/entry.parent).glob(entry.name+'.*'):
                if f.suffix not in ('.uasset','.ubulk','.uexp','.uptnl'):continue
                rel=entry.parent/f.name
                expected=e.get('icon_baseline') if key=='icon' and f.suffix=='.uasset' else None
                writes.append((rel,f.read_bytes(),expected or previous_hashes.get(rel.as_posix())))
            if not (batch/'Host'/entry.with_suffix('.uasset')).is_file():raise FileNotFoundError(entry)
            if key=='icon':
                rel=entry.with_suffix('.png')
                writes.append((rel,(src/'Export'/rel.name).read_bytes(),previous_hashes.get(rel.as_posix())))
        oldpath='/Game/Weapons/FrontierCompoundBow/'+previous+'/'+name+'.'+name
        opt=next(o for o in opts if o['id']=='frontier_'+kind.lower())
        if opt['visual']['bow_part_riser_mesh'] not in {oldpath,e['mesh']}:raise RuntimeError('Concurrent riser catalog revision')
        for a,b in [(oldpath,e['mesh'])]:
            if a.encode() in new:
                if new.count(a.encode())!=1:raise RuntimeError('Ambiguous asset reference')
                new=new.replace(a.encode(),b.encode(),1)
        opt['visual']['bow_part_riser_mesh']=e['mesh']
        if kind=='Aurora':
            first='拉丝银边沿上下弓架收成羽尖。五块极光彩釉嵌进靛蓝底座，釉下细纹从海绿过渡到冰蓝与淡紫。'
            description='镂空弓架从握把两端延伸到弓臂，拉丝银边沿外侧包住五块极光彩釉，釉下细纹由海绿过渡到冰蓝与淡紫。'
            if opt['appearance'] not in (first,description):raise RuntimeError('Appearance text changed independently')
            new=new.replace(first.encode(),description.encode(),1)
            opt['appearance']=description
    if json.loads(new.decode('utf-8-sig'))!=doc:raise RuntimeError('Unrelated catalog edit')
    changes=[]
    for rel,data,expected in writes:
        p=root/rel;prior=p.read_bytes() if p.is_file() else None
        if prior!=data and prior is not None and sha(prior)!=expected:raise RuntimeError('Unrecognized published file: '+str(rel))
        record[rel.as_posix()]=sha(data)
        if prior!=data:changes.append((rel,prior,data))
    if new!=old:changes.append((cat,old,new))
    if not editor and not closed():raise RuntimeError('Active editor: run publication on the existing editor bridge')
    for rel,prior,data in changes:
        path=root/rel
        if not editor and rel.suffix=='.uasset' and not closed():raise RuntimeError('Editor started; retry on its bridge.')
        if (path.read_bytes() if path.is_file() else None)!=prior:raise RuntimeError('Changed during publication: '+str(rel))
        if prior is not None and not (before/rel).exists():atomic(before/rel,prior)
        atomic(path,data)
    for rel,d in record.items():
        if sha((root/rel).read_bytes())!=d:raise RuntimeError('Publication did not land: '+rel)
    r={'revision':'LegendaryFrameFitR2','catalog':cat.as_posix(),'catalog_sha256':sha((root/cat).read_bytes()),
       'installed':record,'import':imported,'Eclipse':json.loads((batch/'Eclipse-fit.json').read_bytes()),
       'Aurora':json.loads((batch/'Aurora-fit.json').read_bytes()),'restore':'Before/Content; previous skeletal mesh packages retained',
       'comparison':str(batch.parents[2]/'ArtReviews/FrontierCompoundBow'/batch.name/'蚀日与极光_同机位结构对照.jpg'),
       'editor_build':'asset-only','in_game_test':False}
    atomic(batch/'published.json',(json.dumps(r,ensure_ascii=False,indent=2)+'\n').encode())
    print('Published both legendary risers and their icons.')
if __name__=='__main__':install(Path(sys.argv[1]),Path(sys.argv[2]))
