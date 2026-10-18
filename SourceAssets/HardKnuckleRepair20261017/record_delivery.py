import hashlib,json
from pathlib import Path

O=Path(__file__).parent;R=O.parents[1]
receipt=json.loads((O/'import_receipt.json').read_text())
review=json.loads((O/'geometry_review.json').read_text())
rows=json.loads((O/'author_receipt.json').read_text())
if not receipt.get('completed') or len(receipt['saved'])!=26:raise RuntimeError('Asset save is incomplete')
assets=[]
for key,entry in receipt['saved'].items():
    file=R/'Content'/(entry['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
    assets.append(dict(key=key,path=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),bytes=file.stat().st_size))
report=dict(item='ue_hardknuckle_gloves',saved_assets=assets,saved_skeletal_bindings=25,
            scoped_geometry_review=str(O/'geometry_review.json'),game_run=False,
            cplusplus_changed=False,compile_required=False,
            source_root=str(O),existing_production_root=str(O.parent/'BenelliM4Super9020261006'))
(O/'delivery.json').write_text(json.dumps(report,indent=2))
table='\n'.join('| '+x['profile']+' | '+str(x['triangles'])+' | '+str(len(x['cuffs']))+' | 已保存 |' for x in rows)
rays=sum(c['rays'] for p in review['profiles'] for c in p['checks'])
doc=f'''# 硬壳战术手套本体与腕口修复 — 2026-10-17

## 根因

`BenelliM4Super9020261006/fix_glove_cuff.py` 的旧 `reorient_mesh` 用右手叉积的朝向重排了 UE 原生三角形。原生 UE 源的面绕序与外法线叉积符号相反；原手套 **11,292 面全部被翻转**。当前 UE M4 手套读回也确认了错误绕序，不只是离线源的问题。

旧补片还用早期 M4 皮肤和腕口位置派生全部手臂。实际腕部隐藏边界不同：M4 等约为腕骨向前臂 4.1–4.6 cm，Super90/M870 为 2.8–3.2 cm，Body/Jason 更靠近腕骨。不能用同一轴向位置封缝。

## 完成修改

- 从补缝前母版恢复每个原生绑定的手套本体；原始位置、权重、面绕序、UV 和法线保持原样。
- 使用当前运行配置所引用的真实裸臂资产，逐绑定制作连续腕部内衬。外壁、内壁和两端包边组成封闭壳层，内衬约 1.6 mm 厚；腕部外侧留约 1.8 mm，手臂端回折到可见皮肤内，另一端搭入原手套。
- 内衬蒙皮由对应裸臂表面重心插值取得。只为实际存在的单手分支制作相应一侧；双手各自匹配。M870 与 Super90 的腕口表面已读回比较，当前共用区域一致。
- 全部 25 个装备绑定和原有掉落模型已实际保存，骨骼模型沿用 3 级 LOD。装备 ID、运行引用、动作、掌指握姿和材质身份保持原样。
- 旧 `fix_glove_cuff.py` 改为新制作入口，移除整件翻面的做法；同步修正掉落 FBX 导出时 UE→Blender 的左右手坐标转换。

## 排查范围与限制

本次针对用户报告进行离线排查：25 个绑定逐一核对原手套未改形、新内衬绕序和闭合壳层；对当前皮肤分支共进行 {rays:,} 条腕部径向射线检查，未发现覆盖区域贯穿到背景的开口。M4 做了带背面剔除的直腕、40° 弯腕前后图像对照。

这些是几何与离线画面证据，没有启动游戏或 PIE，也没有执行全动作运行验收。实际装备、动画与衣袖组合观感由用户确认。本次没有修改 C++，无需重新构建游戏二进制。

## 已保存范围

| 绑定 | LOD0 面数 | 内衬侧数 | 资产状态 |
| --- | ---: | ---: | --- |
{table}

另已保存 `Super90Source20261006/Pickups/SM_ue_hardknuckle_gloves`。

制作与回执：`SourceAssets/HardKnuckleRepair20261017/`。`Before/` 保存改动前源码、作者数据和资产；`Read/` 为本次真实资产读回；`Authored/` 为最终候选；`import_receipt.json` 与 `delivery.json` 为保存及产物散列。
'''
(R/'Docs/Characters/hardknuckle-cuff-repair-20261017.md').write_text(doc,encoding='utf-8')
(O/'README.md').write_text('''# Hardknuckle repair 2026-10-17

Production recipe: `ue_hardknuckle_gloves`, all 25 native bindings plus pickup.

`read_sources.py` exports actual runtime wrist geometry through UE. `author.py` restores the original glove and authors closed cuffs per native skin. `native_transport.py` retains only the prior binding transport. `review_geometry.py` is the scoped investigation, not a routine global test. `import_assets.py` saves all assets with resumable receipts. `publish_sources.py` updates the established production source files after save. The production `fix_glove_cuff.py` delegates to this authoring path.

The UE source face order is clockwise relative to its stored outward normals. Never reverse all triangles according to a right-hand-space visualization. Apply a handedness reflection when entering Blender.

Original body geometry is retained. No game or PIE was launched. Runtime acceptance remains with the user.
''',encoding='utf-8')
print('HARDKNUCKLE_DELIVERY_RECORDED',len(assets))
