import hashlib,json
from pathlib import Path
O=Path(__file__).parent;R=O.parents[1]
receipt=json.loads((O/'import_receipt.json').read_text())
materials=json.loads((O/'material_receipt.json').read_text())
display=json.loads((O/'display_receipt.json').read_text())
published=json.loads((O/'published.json').read_text())
builds={}
for file in sorted(O.glob('Build-*/result.json')):
    result=json.loads(file.read_text(encoding='utf-8-sig'))
    if result.get('build')=='Succeeded':builds[result['target']]=str(file)
if set(builds)!={'FPSGAME','FPSGAMEEditor'}:raise RuntimeError('Regular Game/Editor builds not complete')
paths=[v['asset'] for v in receipt['saved'].values()]+list(materials['saved'].values())+[display[k] for k in ('pickup','icon','material')]
saved=[]
for asset in paths:
    file=R/'Content'/(asset.split('.')[0].removeprefix('/Game/')+'.uasset')
    saved.append(dict(asset=asset,file=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
result=dict(item='ue_st6_sleeves',original_sleeve_bindings=25,body_coverage='native body materials on chest/back/abdomen/shoulders/arms',
            grid=[3,3],existing_item_migration=True,builds=builds,saved=saved,game_run=False,acceptance_tested=False)
(O/'delivery.json').write_text(json.dumps(result,indent=2))
doc='''# ST6 原始衣袖与原生身体材质覆盖 — 2026-10-17

用户否定此前扩展后的整体模型，要求恢复最初袖子，胸背、腹部和肩部以材质覆盖，并统一占格 3×3。

## 已完成

- 以 `BenelliM4Super9020261006/EquipmentSources/source_shirt.json` 为原始供体，恢复 25 个原生绑定；每个袖子源回到 4,286 顶点、8,442 面。Super90/M870 直接保留最初源的几何和权重，其他绑定沿用原始适配方式。
- 移出此前追加的肩部扩展、躯干壳、立领与躯干转锁骨权重。第一人称袖子只保留袖子，身体继续使用已有的完整原生网格和蒙皮。
- 换装组件新增 `base_material_overrides`，通过同一异步加载批次给身体对应材质槽应用布料。胸背与腹部使用分区布料、中央门襟和细缝线，肩臂延续原 ST6 深灰织物；布料取样固定在参考姿态，随身体一起变形。手、头、裤腿、鞋沿用原有装备范围。
- 取消 ST6 的身体隐藏覆盖及 `owner_body_meshes`。本机身体直接显示已有胸腹，原始武器袖子负责第一人称手臂；不会再追加第二套躯干或袖臂网格。
- 恢复后的袖子及 LOD、3 个身体布料材质、掉落材质与模型、320×320 的 3×3 背包图标已实际保存。
- 目录原本已写 3×3，但旧实例快照仍可能保留旧尺寸；已加入 `MigrateAuthoredItemFootprint` 的 ST6 3×3 规则，复用既有背包、仓库和共享容器重新落位逻辑，空间不足时按原流程保留物品。
- 更新旧作者、整衣重建、owner 重建、图标和目录发布入口，避免重建时恢复被否定的躯干壳。

## 构建与交付边界

Game 与 Editor 常规构建均已完成；没有启动游戏、PIE 或额外运行测试。制作图为正式背包图标，不是运行验收截图。具体观感与换装由用户测试。

首次 Game 构建在 UBA 下多个无关编译单元报 MSVC C1001；只停止了本任务失败构建及其子编译进程，随后使用 `-NoUBA` 重建。并行冰甲反射头更新通过重新生成 UHT 处理；内存竞争导致的失败项按增量补编。唯一额外源码修正是 `IceArmorFragments.cpp` 中 `FirstPersonCamera.Get()`，解决新增文件把 `TObjectPtr` 推导为裸指针的编译错误，不改变其功能。

制作、原始备份、资产保存及构建回执位于 `SourceAssets/ST6Reset20261017/`。最终文件散列与构建记录见 `delivery.json`。旧资产保持可恢复，不删除未归属本次任务的内容。
'''
(R/'Docs/Characters/st6-native-body-reset-20261017.md').write_text(doc,encoding='utf-8')
(O/'README.md').write_text('''# ST6 native body reset

`author_sleeves.py` restores the original 2026-10-06 sleeve donor across existing native rigs. `build_materials.py` makes rest-pose anchored cloth for the existing body. `recipe.py` owns only the ST6 equipment recipe. `import_sleeves.py`, `finish_assets.py`, and `publish.py` save assets and merge catalogs. `author_pickup.py` and `render_icon.py` make the display shirt and 3x3 icon. `build.ps1` builds Game or Editor without UBA after the observed compiler failures.

The native body mesh is never expanded or rebound to the first-person clavicles. The owner view uses material coverage instead of an extra torso mesh. Original sleeves retain their own material, UVs, geometry, and native animation binding.

No game/PIE or acceptance tests were launched. Use the saved receipts, not old shell authoring reports, to determine delivery state.
''',encoding='utf-8')
print('ST6_DELIVERY_COMPLETE',len(saved),flush=True)
