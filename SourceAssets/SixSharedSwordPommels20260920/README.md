# 六款剑类通用配重

用户明确要求保留符文剑与寒晶剑各自三款，合并成六款，让当前全部可改造剑共用。此前三款共用版本由本次扩展，不把寒晶旧三款效果覆盖到星系三款上。

| 唯一 ID | 名称 | 保留属性 |
| --- | --- | --- |
| pommel_hardened | 硬化配重 | 重击倍率 +0.15；攻击击退 +10%；攻速 −10%；耐力消耗 +10% |
| pommel_runic | 符文配重 | 魔法冷却 −15%；蓝耗 −15% |
| pommel_mana_orb | 魔力球配重 | 魔法伤害 +10%；蓝耗 +15% |
| ballast_hardened | 陨星锤首 | 快速近战倍率 +0.25；快速近战击退 +50% |
| ballast_rune | 凝碧星核 | 魔法伤害 +15%；蓝耗 +20% |
| ballast_magic_orb | 疾星配重 | 攻速 +15%；蓄力重击倍率 −0.25 |

原装单列，因此每把剑的配重栏共七个选择。当前可改造剑为符文长剑和寒晶剑。新增剑沿用同一目录，在自身适配配置中描述两类已有安装端；不再复制六份改造定义。

六个主体网格全部复用原资产。宿主的 `pommel_profile.interfaces` 按实际安装接口选择位置、比例和连接件；材料主题按槽名覆盖。护手、握把、剑刃和连击保持原流程。

存档保留当前版本三个 `ballast_*` ID 的含义：均对应星系三款。恢复的寒晶旧款用新的独立 ID。更早寒晶旧版与上一轮三款共用版使用了相同 ID 且没有版本标记，无法可靠区分；不猜测并改写用户存档。新增三款可直接选择保存。

## 已完成交付

- `author_reverse_fit.py` / `SixSharedPommels_RuneFit.blend`：保留寒晶旧三款主体，制作一个三款共用的符文剑反向接口，以及三张 1024 RGBA 银色材质实物图标。
- `Export/SM_SwordPommel_RuneToFrost.fbx` / `.glb`：实际端面轮廓连续过渡，长度 6 mm，4560 三角面；FBX 和 Blender 场景为引擎材质制作依据，GLB 不能完整表达混合材质图。
- `import_assets.py` / `import_receipt.json`：银色材质、接口和 12 个新增/公共回退图标已导入保存；原晶体及符文发光结构保留。
- `install_catalog.py` / `integration_receipt.json`：六个唯一选项已写入实际 `melee-gunsmith.json`，两把剑按 `pommel_profile.interfaces` 引用同一共享外观目录。
- `build_receipt.json`：普通 Editor 构建成功，日志 `Saved/BuildEditor/build-20260920-132848.log`；基础 DLL 已包含按源接口选择宿主适配参数的逻辑。

## 当前状态与重建边界

2026-09-20 用户确认“达标了”。六款共享方案为当前采用版本；此前编辑器缓存／重启提示已退出待办。本轮整理没有追加游戏测试。

`restored-options.json` 保存寒晶原三款的独立 ID 与原属性。`install_catalog.py` 不再依赖已归档的 `BeforeShared`；先恢复仓库中的三个模块／共享外观 JSON 与 `melee-gunsmith.json`，再导入所需资产并运行本目录安装入口。不要重跑已退役的三款安装器。

上游仍需保留：`../RuneSwordPommels20260920` 的星系主体、PBR 源与图标；`../SharedSwordPommels20260920` 的正向接口及铜色主题；寒晶模块／旧三款的可编辑源与导入回执；`../MeleeGuards20260915/finish_patch.json`。本目录提供反向接口、银色主题和最终六款合并入口。旧阶段名称不表示源文件已废弃。

公开仓库只发布脚本、目录参数与恢复说明；模型、贴图、图标、UE 资产和密集表面采样留在本机，须先恢复已许可源文件。具体见 [资源恢复](../../Docs/AssetSetup.md) 与 [本轮整理记录](../../Docs/Weapons/six-sword-pommels-publication-20260920.md)。
