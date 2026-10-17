# M870 背包／装备栏图标与腰射扩散

## 图标原因与修改

当前 M870 的手臂槽名为 `MI_Super90JointSkin_Arms`、`MI_Super90JointSkin_Arms_2`。动态图标仍使用旧的 Manny／Hand 识别逻辑，手臂没有被排除，且参与可见顶点的取景范围计算。

装备栏的图区比背包画布更扁。原来按整张带透明边距的画布拟合，枪体又被上下留白压小。

| 路径 | 处理 |
| --- | --- |
| 背包／装备栏动态图标 | 拍摄前剔除手臂材质分区；取景只计可见枪体与已装配部件；M870 配方缓存键更新 |
| 动态画刷 | 发布纹理时复用现有 alpha 轮廓裁剪，保留两像素过滤边距，并按真实轮廓尺寸拟合 |
| 目录备用图 | 更新 `Content/ColdSteelData/Icons/ue_m870.png`；导入画刷时采用相同裁剪规则 |
| 第三人称／枪匠预览／掉落物 | 共用 `WeaponPresentationMaterials::IsArmSection`，同时识别显示槽名与网格原始材质；保留已有局部可见性规则 |

裁剪在图标发布／导入时进行，不在 Paint 中重复读像素。衣物、第一人称动画及游戏内网格无需重导入。

## 数值

`gunsmith.json` 中 `ue_m870.base.spread_mult` 从 **2.25** 改为 **1.2375**：`2.25 × 0.55 = 1.2375`，即默认腰射扩散减少 45%。注册脚本同步使用新值。

`GunsmithSystem::CalculateItem` 读取该基础值，角色的 `HipSpreadMultiplier` 消费最终配件计算值；实时准星继续依据 `GetHipSpread()` 投影，不另改准星像素。

2026-10-17 延长管制作时更正：上述首次目录修改误匹配了 SUPER90 的相同数值块，实际将 SUPER90 改为 1.2375，M870 当时仍为 2.25。现已按武器 ID 定位，正式写入 M870 的 1.2375，并将本次误改的 SUPER90 一项恢复为 2.25；其余 SUPER90 当前配置保留。精确修改回执为 `SourceAssets/M870ExtendedTube20261017/catalog_receipt.json`。

## 制作记录

本轮来源备份和后台构建／目录图导出记录位于 `Tools/Weapons/M870Icons20261017/`。图标由现有 `ColdSteelWeaponIconCatalog` commandlet 只导出 `ue_m870`，不启动游戏或加载玩家存档。游戏内显示与射击手感由用户体验。

- 后台构建成功：`Saved/BuildEditor/build-20261017-084608.log`，包含本轮修改的 UI 与第三人称文件编译及 DLL 链接。
- 目录图已写入：`Content/ColdSteelData/Icons/ue_m870.png`，640×320；导出日志 `SourceAssets/WeaponInventoryIcons20260913/export-ue_m870.log` 返回 `COMPLETE failures=0`。
- 本轮查看生成图，只包含完整枪体，没有手臂；图标发布／备用图导入时的画刷裁剪负责移除画布上下透明边距。未运行游戏做背包、装备栏或射击测试。
