"""Identify this task's superseded artifacts and prepare a verified local archive manifest."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PUB=ROOT/'Docs/Publication/SearchCollectibles20261013'
LOCAL=ROOT/'Saved/SearchCollectiblesPublication20261013'
plan=json.loads((LOCAL/'plan.json').read_text(encoding='utf-8'))
design=json.loads((ROOT/'Docs/Gameplay/search-item-catalog-v2-20261012.json').read_text(encoding='utf-8'))
active=set()
for item in design['items']:
    for key in ('source','fbx','glb'):
        if item.get('model',{}).get(key): active.add((ROOT/item['model'][key]).resolve())
entries={}
def add(path,reason,replacement):
    source=(ROOT/path).resolve()
    if not source.exists(): return
    if not source.is_relative_to(ROOT): raise RuntimeError('Outside workspace')
    files=[source] if source.is_file() else list(source.rglob('*'))
    for file in files:
        if not file.is_file(): continue
        file=file.resolve()
        if file in active: raise RuntimeError('Active model source: '+str(file))
        relative=file.relative_to(ROOT).as_posix()
        target='trash/search-collectibles-20261013/'+relative
        if (ROOT/target).exists(): raise RuntimeError('Archive target already exists: '+target)
        entries[relative]=dict(source=relative,destination=target,bytes=file.stat().st_size,
            sha256=hashlib.sha256(file.read_bytes()).hexdigest(),reason=reason,replacement=replacement)

for folder in plan['source_roots']:
    add('SourceAssets/'+folder+'/Before','Superseded pre-edit snapshot; scoped integration differences exported before archival',
        'Current source/catalog plus Docs/Publication/SearchCollectibles20261013/scene-search-integration.patch')
    for file in (ROOT/'SourceAssets'/folder).glob('Authored/*.blend1'):
        add(file.relative_to(ROOT),'Blender automatic backup; active editable source retained',str(file.relative_to(ROOT))[:-1])
for folder in ('CollectionIconOrientation20261013','CollectionIconLayoutR2_20261013'):
    add('SourceAssets/'+folder+'/PreviousIcons','Superseded inventory textures',
        'Current Content/ColdSteelData/Icons paths and CollectionIconLayoutR2_20261013/Icons')
for part in ('Icons','Previews','inventory_icons.json','model_manifest.json','Scripts/prepare_batch.py','Scripts/render_inventory_icons.py','Scripts/install_icons.py'):
    add('SourceAssets/CollectionIconOrientation20261013/'+part,'Uniform diagonal icon revision superseded by footprint-oriented layout',
        'SourceAssets/CollectionIconLayoutR2_20261013')
add('SourceAssets/ServerNeutralPCB20261013/PreviousRuntimeAppearance','Replaced green PCB appearance backup',
    'Current neutral textures, including retained legacy package aliases')
add('SourceAssets/ServerNeutralPCB20261013/Scripts/build_inventory_migration.ps1','Withdrawn native appearance migration route; resource aliases are the final implementation',
    'SourceAssets/ServerNeutralPCB20261013/Scripts/apply_legacy_appearance.py')
for folder in ('ServerOriginalMarks20261013','ServerNeutralPCB20261013'):
    add('SourceAssets/'+folder+'/previous_models.json','Superseded model manifest snapshot',
        'SourceAssets/'+folder+'/model_manifest.json')
for part in ('Authored','Export','Textures','Scripts','UEImportHost','previous_models.json','model_manifest.json','texture_manifest.json','inventory_icons.json'):
    add('SourceAssets/ServerReferenceRemodel20261013/'+part,'Branded reference production superseded; source reference photos retained separately',
        'SourceAssets/ServerOriginalMarks20261013; reference images remain in ServerReferenceRemodel20261013/Reference')
for part in ('Authored','Export'):
    for file in (ROOT/'SourceAssets/ServerOriginalMarks20261013'/part).glob('*_CSR3*'):
        if '_CSR3B' not in file.name and '_CSR3C' not in file.name:
            add(file.relative_to(ROOT),'First original-mark export superseded by corrected CSR3B geometry / CSR3C UE tangents',
                'SourceAssets/ServerOriginalMarks20261013/model_manifest.json')
old=json.loads((ROOT/'SourceAssets/SearchServerEquipment20261013/model_manifest.json').read_text(encoding='utf-8'))
for key in ('GPU','RAM','SSD'):
    for field in ('source','fbx','glb'):
        add(Path(old['assets'][key][field]).relative_to(ROOT),'Original hardware geometry replaced by reference-based original-mark models',
            'SourceAssets/ServerOriginalMarks20261013')
    for texture in (ROOT/'SourceAssets/SearchServerEquipment20261013/Textures').glob('T_SE_'+key+'_*'):
        add(texture.relative_to(ROOT),'Original hardware textures superseded', 'SourceAssets/ServerOriginalMarks20261013/Textures')
for suffix in ('.json','.md'):
    add('Docs/Gameplay/search-item-catalog-v1-20261012'+suffix,'V1 filler-item design explicitly superseded by utility/value V2',
        'Docs/Gameplay/search-item-catalog-v2-20261012'+suffix)
report=dict(root='D:/FPS3D/FPSGAME',archive='trash/search-collectibles-20261013',status='planned',
    files=list(entries.values()),file_count=len(entries),total_bytes=sum(e['bytes'] for e in entries.values()))
(PUB/'archive-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(files=report['file_count'],bytes=report['total_bytes'],active_model_sources_retained=len(active))))
