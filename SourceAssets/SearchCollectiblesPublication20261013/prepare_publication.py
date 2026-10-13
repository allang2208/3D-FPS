"""Prepare scoped source candidates and integration patch without changing the worktree/index."""
import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PUB=ROOT/'Docs/Publication/SearchCollectibles20261013'
LOCAL=ROOT/'Saved/SearchCollectiblesPublication20261013'
PUB.mkdir(parents=True,exist_ok=True)
LOCAL.mkdir(parents=True,exist_ok=True)

def git(*args):
    return subprocess.check_output(['git','-c','core.safecrlf=false',*args],cwd=ROOT).decode('utf-8')
def read(path): return Path(path).read_text(encoding='utf-8-sig')
def digest(text): return hashlib.sha256(text.encode()).hexdigest()
base=git('rev-parse','HEAD').strip()
def head(path): return git('show',base+':'+path)
def candidate(path,text):
    out=LOCAL/'Candidates'/path;out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(text,encoding='utf-8',newline='\n')
    candidates.append(path)
def replace_once(text,old,new):
    if text.count(old)!=1: raise RuntimeError('Ambiguous edit anchor: '+old[:100])
    return text.replace(old,new,1)
def extract(text,start,end):
    at=text.index(start);return text[at:text.index(end,at)]
candidates=[]

# The unpublished multiplayer baseline must not leak into unrelated native source commits.
patch_paths=['Source/FPSGAME/UI/ColdSteelSceneContainer.h','Source/FPSGAME/UI/ColdSteelSceneContainer.cpp',
 'Source/FPSGAME/UI/ColdSteelStatusModel.h','Source/FPSGAME/Multiplayer/ColdSteelSharedContainers.cpp',
 'Source/FPSGAME/Multiplayer/ColdSteelSharedInventorySubsystem.h','Source/FPSGAME/Multiplayer/ColdSteelInventoryRequests.cpp']
chunks=[];patch_manifest=[]
for path in patch_paths:
    before=ROOT/'SourceAssets/FacilitySearchLoot20261013/Before'/path
    if not before.exists(): before=ROOT/'trash/search-collectibles-20261013/SourceAssets/FacilitySearchLoot20261013/Before'/path
    old=read(before);new=read(ROOT/path)
    if path.endswith('ColdSteelStatusModel.h'):
        marker='    /** Stage a facility search result and its claim together; caller owns the durable commit. */\n'
        block=extract(new,marker,'    /** 测试箱专用')
        new=replace_once(old,'    /** 测试箱专用',block+'    /** 测试箱专用')
    diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path,tofile='b/'+path,n=3))
    chunks.append('diff --git a/'+path+' b/'+path+'\n'+diff)
    patch_manifest.append(dict(path=path,base_sha256_lf=digest(old),result_sha256_lf=digest(new)))
for path in ['Source/FPSGAME/UI/ColdSteelSceneLoot.h','Source/FPSGAME/UI/ColdSteelSceneLoot.cpp']:
    new=read(ROOT/path)
    chunks.append('diff --git a/'+path+' b/'+path+'\nnew file mode 100644\n'+''.join(difflib.unified_diff([],new.splitlines(True),fromfile='/dev/null',tofile='b/'+path,n=3)))
    patch_manifest.append(dict(path=path,base_sha256_lf=None,result_sha256_lf=digest(new)))
(PUB/'scene-search-integration.patch').write_text(''.join(chunks),encoding='utf-8',newline='\n')
(PUB/'integration-baseline.json').write_text(json.dumps(dict(status='requires_unpublished_shared_inventory_baseline',
    note='Patch is already applied in the full local workspace. Do not apply it twice. This is not a standalone multiplayer framework.',files=patch_manifest),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Item definitions: only 17 collectibles and the two requested rarity edits.
path='Content/ColdSteelData/items.json';text=head(path);current=json.loads(read(ROOT/path));decoder=json.JSONDecoder()
for id in ('soda_can','baguette_bread'):
    match=re.search(r'^  '+re.escape(json.dumps(id))+r':\s*',text,re.M)
    start=match.end();item,length=decoder.raw_decode(text[start:]);item['rarity']=current[id]['rarity']
    text=text[:start]+json.dumps(item,ensure_ascii=False,indent=2).replace('\n','\n  ')+text[start+length:]
ids=[id for id in current if id.startswith('search_')]
if len(ids)!=17: raise RuntimeError('Unexpected collectible scope')
existing=json.loads(text)
for id in ids:
    if id in existing: raise RuntimeError('Collectible already committed; re-evaluate base')
blocks=['  '+json.dumps(id)+': '+json.dumps(current[id],ensure_ascii=False,indent=2).replace('\n','\n  ') for id in ids]
text=text.rstrip();text=text[:-1].rstrip()+',\n'+',\n'.join(blocks)+'\n}\n'
candidate(path,text)

path='Source/FPSGAME/UI/ColdSteelInventoryPresentation.cpp';text=head(path);current_text=read(ROOT/path)
start='        FLinearColor CardFill=Hovered?';end='        Box(X+8,Y+2,W-16,1,'
text=replace_once(text,'        DrawCard(Hovered?GunsmithUI::Gray(80,175):GunsmithUI::Gray(55,128),FLinearColor::Transparent,1);\n',extract(current_text,start,end))
candidate(path,text)

path='Source/FPSGAME/UI/ColdSteelPickupConsumable.cpp';text=head(path);current_text=read(ROOT/path)
block=extract(current_text,'    const bool bDocumentCollectible=', '    {\n        auto* Asset=LoadObject<UStaticMesh>')
text=replace_once(text,'    if(Id==TEXT("baguette_bread")||Id==TEXT("bread")||Id==TEXT("soda_can"))\n',block)
candidate(path,text)

path='Source/FPSGAME/UI/ColdSteelInventoryRules.cpp';text=head(path)
text=replace_once(text,'        {nullptr,TEXT("ue_alchemy_spellbook"),2,2},\n',
    '        {nullptr,TEXT("ue_alchemy_spellbook"),2,2},\n        {nullptr,TEXT("search_graphics_card"),2,1},\n')
at=text.index('bool MigrateAuthoredGridFootprints(');first=text[:at];tail=text[at:]
tail=replace_once(tail,'        ApplyOrientation(Item,0);\n',
    '        // GPU shrinks from 3x2 to 2x1; preserve its chosen rotation and cell.\n        ApplyOrientation(Item,Item.Definition==TEXT("search_graphics_card")?-1:0);\n')
candidate(path,first+tail)

path='Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp';text=head(path);current_text=read(ROOT/path)
block=extract(current_text,'            // Reference-remodeled server props','            // Animated consumable effects')
text=replace_once(text,'            // Animated consumable effects',block+'            // Animated consumable effects')
block=extract(current_text,'                // These two consumables now use the green catalog tier','                if(PotionUpdated)')
text=replace_once(text,'                if(PotionUpdated)',block+'                if(PotionUpdated)')
candidate(path,text)

path='Config/DefaultGame.ini';text=head(path).rstrip()+'\n\n; Authored search collectible assets; licensed binary payloads remain local.\n[/Script/UnrealEd.ProjectPackagingSettings]\n'
for directory in ('SearchDocuments20261012','SearchMaintenance20261012','SearchServerEquipment20261013','ServerOriginalMarks20261013/Final','ServerNeutralPCB20261013'):
    text+='+DirectoriesToAlwaysCook=(Path="/Game/Items/'+directory+'")\n'
candidate(path,text)

# Ignore only this work's media, import hosts, local evidence and staging state.
task_roots=['SearchDocuments20261012','SearchMaintenance20261012','SearchServerEquipment20261013','ServerOriginalMarks20261013',
 'ServerNeutralPCB20261013','ServerReferenceRemodel20261013','CollectionIconOrientation20261013','CollectionIconLayoutR2_20261013',
 'FacilitySearchLoot20261013','FacilitySearchLootGuaranteed20261013']
ignore='\n# Search collectibles: publish recipes, not binary assets, import hosts or local receipts.\n'
for folder in task_roots:
    ignore+=f'/SourceAssets/{folder}/**\n!/SourceAssets/{folder}/**/\n!/SourceAssets/{folder}/Scripts/\n!/SourceAssets/{folder}/Scripts/*.py\n!/SourceAssets/{folder}/Scripts/*.ps1\n!/SourceAssets/{folder}/Scripts/*.cjs\n!/SourceAssets/{folder}/README.md\n'
ignore+='/SourceAssets/SearchCollectiblesPublication20261013/**\n!/SourceAssets/SearchCollectiblesPublication20261013/*.py\n!/SourceAssets/SearchCollectiblesPublication20261013/*.ps1\n'
path='.gitignore';working=read(ROOT/path)
if '# Search collectibles: publish recipes' not in working:(ROOT/path).write_text(working.rstrip()+'\n'+ignore,encoding='utf-8')
candidate(path,head(path).rstrip()+'\n'+ignore)

# The original chest JSON bug repair is local; its remote diff only contains another task's currency/dealer edits.
(LOCAL/'plan.json').write_text(json.dumps(dict(base=base,candidates=candidates,source_roots=task_roots,collectibles=ids,
  integration_publication='scoped patch only; full local integration left untouched'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(base=base,partial_candidates=candidates,integration_patch_paths=len(patch_manifest)),ensure_ascii=False))
