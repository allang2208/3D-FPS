"""Publish only the corrected arcane appearance, preserving item instances/stats."""
import os,shutil,uuid,sys
from combat_belts_common import *
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
import json_entries as entries
root=P/'SourceAssets/ArcaneConduitBelt20261025/KeeperFixR2';out=root/'arcane'
saved=read(out/'saved_assets.json');execution=read(R/'asset-execution.json')
checks=read(root/'saved-geometry-checks.json');offline=read(root/'offline-checks.json')
if not (saved['completed'] and checks['completed'] and offline['completed']):raise RuntimeError('Finish scoped asset checks first')
if execution['exit_code']!=0 or execution['script']!='save_arcane_keeper_fix.py' or execution['script_sha256']!=sha(P/'Tools/CombatBeltsIntegration/save_arcane_keeper_fix.py'):
    raise RuntimeError('Finish the arcane asset batch first')
if saved['source_manifest_sha256']!=sha(out/'delivery.json'):raise RuntimeError('Arcane delivery changed since saving')
key='ue_arcane_conduit_belt';data_dir=P/'Content/ColdSteelData'
changes=[]
for filename in ('items.json','modular_outfits.json'):
    path=data_dir/filename;before=path.read_bytes();text=before.decode('utf-8-sig');data=read(path)
    if filename=='items.json':
        text=entries.replace(text,[key,'world_mesh'],saved['pickup']['asset'])
    else:
        for body,parent in (('Jason',['items',key]),('Kaitlin',['body_variants','kaitlin','items',key])):
            for field in ('rig_meshes','owner_body_meshes'):
                text=entries.replace(text,parent+[field,body],saved['wear'][body]['asset'])
            text=entries.replace(text,parent+['source_revision'],'ArcaneConduitBelt20261025/KeeperFixR2')
    after=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
    changes.append((path,before,after))
for path,before,after in changes:
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog edit: '+str(path))
for path,before,after in changes:
    backup=root/'Before'/path.name;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    temp=path.with_name(path.name+'.arcane-keeper-'+uuid.uuid4().hex+'.tmp');temp.write_bytes(after)
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog writer: '+str(path))
    os.replace(temp,path)
item=read(data_dir/'items.json')[key]
for target in (data_dir/item['ue_icon'],data_dir/'Icons'/(key+'.png')):
    backup=root/'Before'/('icon-'+str(len(target.parts))+'-'+target.name)
    if target.exists() and not backup.exists():shutil.copy2(target,backup)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(out/(key+'.png'),target)
write(root/'asset-execution.json',execution)
write(root/'published.json',dict(completed=True,item=key,assets=saved,configuration='Current items.json and both modular_outfits body branches',
    old_pickup_path_compatibility=checks['compatibility_pickup'],offline_checks=offline,render_lod_checks=checks['render_lods'],
    runtime_tested=False,multiplayer_tested=False,cpp_changes=False))
write(root/'status.json',dict(stage='saved_checked_and_published',ue_assets_saved=True,configuration_published=True,
    offline_checked=True,saved_render_lods_checked=True,runtime_tested=False,multiplayer_tested=False))
write(root.parent/'ModelR2/delivery.json',dict(completed=True,unreal_assets_imported=True,item_catalog_published=True,
    integration_receipt=str(root/'published.json'),runtime_tested=False))
for body in ('Jason','Kaitlin'):
    path=root.parent/'ModelR2/Authored'/f'{body}_production.json';record=read(path)
    record.update(game_integrated=True,integration_receipt=str(root/'published.json'));write(path,record)
previous=R/'arcane/published.json';record=read(previous);record['superseded_by']=str(root/'published.json');write(previous,record)
aggregate=R/'delivery.json';record=read(aggregate);record['latest_arcane_revision']=str(root/'published.json');write(aggregate,record)
doc=P/'Docs/Items/arcane-belt-keeper-fix-20261025.md'
lines=['# 星律导能腰带头顶悬浮修复','',
    '根因是 `author.py::tailoring` 给固定钉设置局部坐标后，没有在下一只皮革固定环之前恢复世界坐标。后侧 3 个固定环的原生腰线又被叠加一次腰部变换；绑定没有指向头部，错误已经存在于源几何中。','',
    '修复在每只固定环开始时恢复世界坐标，保留原本形状、尺寸及材质，重新从对应腰部位置采样权重。ModelR1 保留，ModelR2 保存修正版可编辑 Blend、FBX、GLB；男女三级 LOD、正面物品图标和静态掉落网格同步重制。','',
    '| 身体 | 修复前 LOD0 高度范围（cm） | 修复后 LOD0 高度范围（cm） |','| --- | --- | --- |']
for v in offline['records']:
    if v['lod']==0:lines.append('| '+v['body']+' | '+('%.2f–%.2f'%tuple(v['old_lod0_z_cm']))+' | '+('%.2f–%.2f'%tuple(v['z_cm']))+' |')
lines += ['',
    '已完成本次授权范围内的组件几何、六份 LOD 权重以及 UE 已保存渲染 LOD 回读检查。所有组件处于腰部范围，未发现空权重或头颈权重。未启动游戏或联机测试，也未重新验收其他服装/动作组合。','',
    '新穿戴资源位于 `/Game/Characters/ModularOutfit20260924/ArcaneConduitBelt20261025/KeeperFixR2`，两种身体的 world/owner 配方均已切换。旧物品实例可能保留旧掉落路径，该路径的网格也已同步修正，修改前包保存在 KeeperFixR2/Before。物品 ID、强化和战斗属性保持原值，无需修改 C++ 或重新构建。','',
    '重新进入游玩后加载修正版。生产入口：Blender `Tools/ArcaneConduitBelt/keeper_fix.py` → Blender `Tools/CombatBeltsIntegration/prepare_arcane_keeper_fix.py` → Python `check_arcane_keeper_fix.py` → 现有互斥桥执行 `save_arcane_keeper_fix.py` → Python `publish_arcane_keeper_fix.py`。','',
    '执行和检查记录：`SourceAssets/ArcaneConduitBelt20261025/KeeperFixR2/published.json`。']
doc.write_text('\n'.join(lines)+'\n',encoding='utf-8')
for name in ('Tools/ArcaneConduitBelt/README.md','Docs/Items/combat-belts-integration-20261025.md'):
    path=P/name;text=path.read_text(encoding='utf-8-sig');marker='\n## 星律固定环修复（KeeperFixR2）\n'
    if marker in text:text=text.split(marker,1)[0]
    text+=marker+'\n当前星律穿戴已切换到 KeeperFixR2，修复 3 个皮革固定环被重复变换到头顶的问题，男女全部 LOD、图标和掉落模型同步更新。源模型为 ModelR2；本页原 IntegrationR1 为历史记录。详情见 `Docs/Items/arcane-belt-keeper-fix-20261025.md`。未运行游戏/联机测试。\n'
    path.write_text(text,encoding='utf-8')
print('ARCANE_KEEPER_FIX_PUBLISHED',flush=True)
