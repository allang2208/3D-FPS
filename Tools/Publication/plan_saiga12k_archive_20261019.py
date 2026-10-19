"""Prepare the reviewed retirement manifest; never move assets or run Unreal."""
import hashlib,json,os,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PUB=ROOT/'Docs/Publication/Saiga12K20261019'
LOCAL=ROOT/'SourceAssets/Saiga12KPublication20261019'
TRASH=ROOT/'trash/saiga12k-retired-20261019'
groups=[]
def add(path,reason,replacement):
    p=ROOT/path
    if p.exists():groups.append({'source':path,'destination':(TRASH/p.relative_to(ROOT)).relative_to(ROOT).as_posix(),'reason':reason,'replacement':replacement})
for d in (ROOT/'SourceAssets').iterdir():
    if not d.name.startswith(('Saiga12K','S12KStock')) or d.name=='Saiga12KPublication20261019':continue
    for sub in ('Before','SourceBefore'):
        add((d/sub).relative_to(ROOT).as_posix(),'Superseded rollback snapshot; retain recoverably, outside the active authoring chain.','Current assets and SourceAssets/Saiga12KPublication20261019/Prerequisites')
    for sub in ('DerivedDataCache','IsolatedHost'):
        add((d/sub).relative_to(ROOT).as_posix(),'Completed temporary diagnostic host/cache; junction targets are not retired.','D:/FPS3D/FPSGAME/FPSGAME.uproject and current build outputs')
add('SourceAssets/Saiga12KBumpStockConcept20261018','Old stock concept superseded by user reference.','SourceAssets/S12KStockReference20261018/Reference/user-stock.png')
for sub in ('Authoring','Icons','Textures'):
    add('SourceAssets/Saiga12KSpecialStock20261018/'+sub,'Previous stock shape replaced by reference-led model.','SourceAssets/S12KStockReference20261018/'+sub)
for f in ('Preview/12K_ThunderDrum_Concept_V01.png','design-prompt.txt','generation-v01.json'):
    add('SourceAssets/Saiga12KLegendaryDrumConcept20261018/'+f,'Rejected sideways drum orientation and old display name.','SourceAssets/Saiga12KLegendaryDrumConcept20261018/Preview/12k_Drum_Concept_V02.png')
for f in ('Receipts/before','Receipts/catalog-initial-assumption.json','Receipts/Wire/20261019-111005'):
    add('SourceAssets/Saiga12KNetwork20261019/'+f,'Completed failed/superseded diagnostic attempt; successful presentation evidence copied separately.','Docs/Publication/Saiga12K20261019/Evidence and final Wire/20261019-111539')
for f in ('Receipts/read-01.txt','Receipts/read-02.txt','Receipts/stop-play.txt'):
    add('SourceAssets/Saiga12KResonance20261019/'+f,'Superseded input read or expired one-time editor operation.','SourceAssets/Saiga12KResonance20261019/Inputs and Receipts/saved.json')
retired_tools={
 'Saiga12K':['integrate_source.py','register_data.py'],
 'Saiga12KMagazine':['close_editor.py','finish_editor.py'],
 'Saiga12KRefine':['close_editor.py','end_play.py','build_window.py'],
 'Saiga12KInspect':['install_independent.ps1'],
 'Saiga12KInspectClearance':['save_authorized.ps1'],
 'Saiga12KSpecialStock':['author_model.py','bake_surface.py','install_surface.py','refresh_surface.py','render_icon.py','install_icon.py','save_authorized.ps1','run_ue.ps1','build_editor.ps1','build_game.ps1'],
 'Saiga12KClosure':['snapshot_host.ps1','sync_ddc.ps1','catalog.ps1','render_review.ps1','ue_step.ps1','finalize.ps1'],
 'Saiga12KThirdPerson':['run_authorized_audit.ps1'],
 'Saiga12KReloadReturn':['read_scoped.ps1','save_scoped.ps1'],
 'Saiga12KResonance':['stop_play.py'],
}
for d,files in retired_tools.items():
    for f in files:add('Tools/'+d+'/'+f,'One-time operation, expired lock exception, obsolete host launcher or superseded initial integration.','Current author scripts, explicit integration patches and standard MCP batch gate')

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
files=[];links=[]
for group in groups:
    source=ROOT/group['source'];dest=ROOT/group['destination']
    assert source.resolve().is_relative_to(ROOT) and dest.resolve().is_relative_to(TRASH)
    assert not dest.exists(),str(dest)
    stack=[source]
    while stack:
        p=stack.pop();target=dest/p.relative_to(source);attrs=p.lstat().st_file_attributes
        row={'source':p.relative_to(ROOT).as_posix(),'destination':target.relative_to(ROOT).as_posix()}
        if attrs&stat.FILE_ATTRIBUTE_REPARSE_POINT:
            row['link_target']=os.readlink(p);links.append(row)
        elif p.is_dir():stack.extend(p.iterdir())
        else:
            row.update(bytes=p.stat().st_size,sha256=digest(p),reason=group['reason'],replacement=group['replacement']);files.append(row)
    group['files']=sum(1 for r in files if r['source']==group['source'] or r['source'].startswith(group['source']+'/'))
    group['bytes']=sum(r['bytes'] for r in files if r['source']==group['source'] or r['source'].startswith(group['source']+'/'))
LOCAL.mkdir(parents=True,exist_ok=True)
manifest=LOCAL/'retired-files.json';manifest.write_text(json.dumps({'root':str(ROOT),'trash':str(TRASH),'groups':groups,'files':files,'links':links},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
summary={'local_manifest':manifest.relative_to(ROOT).as_posix(),'manifest_sha256':digest(manifest),'files':len(files),'bytes':sum(r['bytes'] for r in files),'junctions_not_traversed':len(links),'groups':groups}
(PUB/'archive-plan.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in summary.items() if k!='groups'}))
