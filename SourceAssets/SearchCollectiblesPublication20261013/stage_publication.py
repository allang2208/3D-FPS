"""Stage this publication into a private index; preserve the shared working tree and index."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LOCAL=ROOT/'Saved/SearchCollectiblesPublication20261013'
PUB=ROOT/'Docs/Publication/SearchCollectibles20261013'
plan=json.loads((LOCAL/'plan.json').read_text(encoding='utf-8'))
env=os.environ.copy();env['GIT_INDEX_FILE']=str(LOCAL/'publish.index')
def git(*args,input=None,private=False):
    r=subprocess.run(['git','-c','core.safecrlf=false',*args],cwd=ROOT,env=env if private else None,
                     input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if r.returncode: raise RuntimeError((r.stdout+r.stderr).decode('utf-8',errors='replace'))
    return r.stdout
base=git('rev-parse','HEAD').decode().strip()
if base!=plan['base']: raise RuntimeError('HEAD moved; regenerate scoped candidates before staging')

section='''## 搜索收集物、两厅投放与联机接入（2026-10-13）

公开17件收集物的原创制作配方、物品目录、形态图标规则、31个容器的1～3件概率配置及相关库存改动。完整本机已有共享搜索实现并完成构建；其依赖的共享库存框架尚未提交，因此本次联机源码以带基线哈希的接入补丁发布，不能视为公开仓库已获得完整联机框架。模型/PBR、参考图、UE包、日志和构建产物留本机。224份废案/旧快照已移入trash并核对散列；恢复链、补丁前置条件、构建及未实机联测边界见 [搜索收集物整理发布](Publication/SearchCollectibles20261013/README.md)。

'''
path='Docs/AssetSetup.md';working=(ROOT/path).read_text(encoding='utf-8-sig')
title='# 恢复完整 UE5 内容\n\n'
if section not in working:
    (ROOT/path).write_text(working.replace(title,title+section,1),encoding='utf-8')
original=git('show',base+':'+path).decode('utf-8')
(LOCAL/'Candidates'/path).parent.mkdir(parents=True,exist_ok=True)
(LOCAL/'Candidates'/path).write_text(original.replace(title,title+section,1),encoding='utf-8')
if path not in plan['candidates']:plan['candidates'].append(path)

# Preserve the separate, unpublished conversion of skill entrypoints into local forwarders.
for skill,reference,label in (
    ('ue5-world-interaction','facility-search-containers.md','设施搜索柜、掉落概率、共享取物与存档'),
    ('ue5-item-asset-workflow','search-collectible-assets.md','文件、检修材料、服务器硬件与收集物图标')):
    path=f'skills/{skill}/SKILL.md'
    entry=git('show',base+':'+path).decode('utf-8').rstrip()+f'\n\n- {label}：读取 [项目制作合同](references/{reference})。\n'
    dest=LOCAL/'Candidates'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(entry,encoding='utf-8')
    if path not in plan['candidates']:plan['candidates'].append(path)

# Blank context lines are required syntax inside a unified diff, not accidental prose whitespace.
path='.gitattributes';attribute='Docs/Publication/SearchCollectibles20261013/*.patch whitespace=-blank-at-eol\n'
working=(ROOT/path).read_text(encoding='utf-8-sig')
if attribute not in working:(ROOT/path).write_text(working.rstrip()+'\n'+attribute,encoding='utf-8')
dest=LOCAL/'Candidates'/path;dest.write_text(git('show',base+':'+path).decode().rstrip()+'\n'+attribute,encoding='utf-8')
if path not in plan['candidates']:plan['candidates'].append(path)

direct=['Content/ColdSteelData/scene_search_loot.json','Tools/AssetPipeline/collection_icon_orientation.py',
 'Docs/Gameplay/search-container-groups-20261012.json','Docs/Gameplay/search-container-groups-20261012.md',
 'Docs/Gameplay/search-item-catalog-v2-20261012.json','Docs/Gameplay/search-item-catalog-v2-20261012.md',
 'Docs/Gameplay/facility-search-loot-20261013.md',
 'skills/ue5-world-interaction/SKILL.md','skills/ue5-world-interaction/references/facility-search-containers.md',
 'skills/ue5-item-asset-workflow/SKILL.md','skills/ue5-item-asset-workflow/references/search-collectible-assets.md']
direct+=['Docs/Art/'+name+'.md' for name in ('collection-icon-layout-r2-20261013','collection-icon-orientation-20261013',
 'search-documents-models-20261012','search-maintenance-models-20261012','search-server-equipment-models-20261013',
 'server-neutral-pcb-20261013','server-original-marks-20261013','server-reference-remodel-20261013')]
for folder in plan['source_roots']:
    root=ROOT/'SourceAssets'/folder
    for path in (root/'Scripts').glob('*'):
        if path.is_file() and path.suffix in ('.py','.ps1','.cjs'):direct.append(path.relative_to(ROOT).as_posix())
    if (root/'README.md').exists():direct.append((root/'README.md').relative_to(ROOT).as_posix())
for path in (ROOT/'SourceAssets/SearchCollectiblesPublication20261013').glob('*'):
    if path.is_file() and path.suffix in ('.py','.ps1'):direct.append(path.relative_to(ROOT).as_posix())
direct += [path.relative_to(ROOT).as_posix() for path in PUB.glob('*') if path.is_file() and path.name!='published-files.json']

# Snapshot index entries before touching our private index. Later commit only refreshes unchanged entries in the real index.
paths=sorted(set(direct+plan['candidates']+['Docs/Publication/SearchCollectibles20261013/published-files.json']))
real_index={}
for path in paths: real_index[path]=git('ls-files','--stage','--',path).decode()
(LOCAL/'real-index-before.json').write_text(json.dumps(real_index,indent=2),encoding='utf-8')
summary=dict(base=base,publication='scoped_source_and_multiplayer_integration_patch',
  whole_files=sorted(set(direct)-set(plan['candidates'])),partial_files=plan['candidates'],binary_assets_published=False,
  multiplayer_framework_published=False,gameplay_tests_run_this_turn=False)
(PUB/'published-files.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
git('read-tree',base,private=True)
for path in paths:
    source=LOCAL/'Candidates'/path if path in plan['candidates'] else ROOT/path
    raw=source.read_bytes()
    # All allowed payloads are UTF-8 source, recipes or prose, never binary media.
    text=raw.decode('utf-8-sig').replace('\r\n','\n')
    if '\x00' in text or len(raw)>2*1024*1024: raise RuntimeError('Unexpected binary/large payload: '+path)
    oid=git('hash-object','-w','--stdin',input=text.encode()).decode().strip()
    git('update-index','--add','--cacheinfo','100644',oid,path,private=True)
git('diff','--cached','--check',private=True)
diff=git('diff','--cached','--no-ext-diff','--no-color',private=True)
(LOCAL/'staged.diff').write_bytes(diff)
(LOCAL/'staged-stat.txt').write_bytes(git('diff','--cached','--stat',private=True))
plan.update(paths=paths,index=str(LOCAL/'publish.index'))
(LOCAL/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(base=base,files=len(paths),diff_bytes=len(diff),index=plan['index']),ensure_ascii=False))
