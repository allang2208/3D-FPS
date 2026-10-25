# 特勤重载远征背包

用户将第七款正式命名为“特勤重载远征背包”，提供 `C:/Users/allan/Downloads/Meshy_AI_Rugged_Expedition_Pac_1024095908_texture.glb`。概念阶段的“界航”仅是旧暂名；生产 ID 为 `ue_special_duty_backpack`，源目录为 `SourceAssets/SpecialDutyBackpack20261024/`。

## 规格与制作

- 沿用模型交接前的容量草案：主背包增加 5 行／90 格，装备后主包 18×9；夹层 14×6／84 格；物品自身 4×4。其他六款容量不变。
- 保留原 GLB 的 154556 个顶点、195009 个三角面及 BaseColor、MetallicRoughness、Normal 三张 PBR 贴图。按原比例统一缩放至高 72 cm，宽约 44.41 cm，完整空载深度约 37.64 cm（包括展开背带），不横向挤压或减面。
- 显示源保持完整空载背包，外侧正面 −Y、顶部 +Z。穿戴源保留实际后背垫，将超出背垫表面的原空载肩腰带连续收整；局部导数始终为正，面、UV 和法线一起保留／变换。
- 当前 Jason／Kaitlin 裸身与六种上衣，共 14 套独立贴身背带，包含新增 `ue_work_jacket`。补取当前保存衣物表面共 146 份输入，每个身体的腰部仍纳入 22 个普通／靴型裤网格路由。
- 使用本款后表面和当前躯干／腰部共同标定安装角，再逐上衣求包体位置。肩带、胸带、腰封、扣件和包体缝接点共用原生骨架与同一动态变换；不复用远界的最终安装角或偏移。
- 共享包体使用 Nanite，贴身带段单独蒙皮。采用有界装饰惯性，频率 3 Hz、阻尼 1.05、角度上限 1.2°、跳动 0.15 cm、总行程上限 1.3 cm；支撑枢轴和范围根据本款包体重新计算。

## 接入

工具为 `Tools/SpecialDutyBackpack/`，制作修订为 `MeshyFitR1_20261024`，UE 目录为 `/Game/Characters/SpecialDutyBackpack20261024/MeshyFitR1_20261024/`。制作链依次为 `prepare_source.py`、`read_fit_r2.py`、`author_r2.py`、`prepare_buffers.py`、`save_assets.py`、`publish.py`、定向 `export_icon` 和 `finish_icon.py`。

`player_body.json` 使用字段事务，仅新增本款的男女装备定义；`items.json` 仅新增本款目录项。Cook 根目录单独登记，掉落通过本款 `world_mesh` 接入现有物理拾取流程。目录容量、装备复制、换装重建和存档沿用既有通用实现，无新增运行时代码分支。

正式图标使用游戏同一装备图标棚，输出 `Content/ColdSteelData/Icons/ue_special_duty_backpack.png`，采用外侧正面、正交平视的统一标准。离线导出完整加载贴图，不改游戏流送设置。

实际保存、本地接入、正式图标状态分别以修订目录的 `saved_assets.json`、`published.json`、`Icon/exported.json` 为准。本轮没有启动交互编辑器、游戏或执行动作／联机测试；不改写玩家存档。用户重启后读取新增目录与模型绑定，再自行体验。

2026-10-24 18:11 已完成后台保存和本地接入：两份静态包体、材质与 14 套男女背带已保存，新目录项及角色引用已写入。正式 320×320 透明正面图标已导出并归档为 `MeshyFitR1_20261024/Icon/ue_catalog_front.png`；生产日志记录 `WeaponIconCatalog: COMPLETE failures=0`。
