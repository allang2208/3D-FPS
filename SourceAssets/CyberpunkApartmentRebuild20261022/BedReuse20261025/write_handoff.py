"""Write delivery notes from the completed production save receipt."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
PROJECT=R.parents[2]
receipt=json.loads((R/'installed.json').read_text('utf8'))
if receipt['stage']!='formal_apartment_beds_saved':raise RuntimeError('Save is still pending')
initial_backup=sorted((R/'Backups').glob('*/L_CyberpunkApartment.umap'))[0]
text=f'''# 公寓其余卧室复用升级床铺（2026-10-25）

正式场景：`/Game/GameMaps/L_CyberpunkApartment`。
实际保存时间：`{receipt['saved_at']}`。

现有公寓保留 Bed2、Bed3 两间卧室；原 Master 区域此前已改成书房。
本批将 Bed3 原床 `AP_Bed3_Bed` 原位替换为 Bed2 已升级的 V3 床，包含床架、床垫、枕头、被褥和封闭灯罩的床头灯。
复用同一份网格与已校准的材质实例，包含原有法线和粗糙度贴图，不复制模型资产。

新增 `AP_Bed3_FootThrow`，复用 V3 床尾毯，按床局部原点挂接，使后续移动床位时随床移动；床尾毯不参与碰撞。
原床 Actor、位置 `(2620, -1862.8, 1.8)` 厘米、朝向和缩放 `(1.4, 1.4, 1)` 保留。
沿用新床已有的双人休息网格配置、67 厘米休息平面与左右位置；不覆盖玩家动作和共享配置。
没有新增独立灯光、房间或测试地图，也未更动其他家具。

## 制作与重建入口

本批局部入口：`SourceAssets/CyberpunkApartmentRebuild20261022/BedReuse20261025/install_level.py`。
原卧室正式接入器在安装 Bed2 后继续调用本批 `apply_upgrade(world)`；旧公寓重建链因此保留新床。
首次安装只处理 Bed3，不重跑全场景或 Bed2 布局安装。
接入使用项目现有批次互斥。编辑器随后退出，最终改由无界面 commandlet 保存；未关闭或重新启动交互编辑器。

## 保存与恢复记录

- 回执：`SourceAssets/CyberpunkApartmentRebuild20261022/BedReuse20261025/installed.json`
- 本批首次修改前地图备份：`{initial_backup}`
- 最终后台保存前的地图快照：`{receipt['backup']}`（编辑器退出时已保留部分替换，后台补齐床尾毯相对变换并保存）
- 保存后地图 SHA256：`{receipt['map_sha256']}`
- 复用网格 2 个，新增模型资产 0 个，新增地图 0 个。

本轮仅完成资源接入与正式地图保存，没有运行游戏测试、穿模检查、截图或渲染；由用户体验。
'''
(PROJECT/'Docs/CyberpunkApartment-BedReuse-20261025.md').write_text(text,encoding='utf8')
(R/'README.md').write_text(text,encoding='utf8')
for name in ('CyberpunkBedroom-Integration-20261024.md','CyberpunkApartment-POSITION-AND-TODO.md'):
    path=PROJECT/'Docs'/name
    old=path.read_text('utf8')
    link='CyberpunkApartment-BedReuse-20261025.md'
    if link not in old:
        path.write_text(old+'\n\n> 2026-10-25：其余现有卧室已复用升级床铺，见 [床铺复用记录]('+link+')。\n',encoding='utf8')
print('BED_REUSE_HANDOFF_WRITTEN')
