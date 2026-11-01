# 贯雷锤座 V2

本轮交付按 `Design/GuanLei_Design.png` 重建中央锤座实体：锻钢整壳、双面北欧雷纹徽章、八点铆钉、车削银边、嵌入式导雷槽与上下编纹板。

- 可编辑模型：`GuanLeiSeatV2_Editable.blend`，FBX 位于 `Export/`。
- PBR：`Textures/` 中 2048 px BaseColor、ORM、Normal、Emissive；原始接口条带继续使用原武器表面材质。
- 沿用 `thunder_god_hammer_modular_v1` 坐标及三处原切面。设计图为造型参考，安装宽度 130 mm、锤颈位置 Z=842 mm；冠部按实际装配定在 Z=1001 mm。模型记录见 `model_manifest.json`。
- UE：`/Game/Weapons/ThunderGodHammer20261028/GuanLeiRebuildV2/SM_ThunderHammer_GuanLeiSeatV2`；`import_receipt.json` 记录已保存资源，`publish_receipt.json` 记录运行目录切换。
- 工坊图标：`../FactoryIconsV2/`。原装实体为中央锤座、双侧锤头、握持包覆、柄尾配重；另生成新版贯雷锤座图标。原装符文是无附加符文，保留既有标准减号图。固定锤颈与木柄不属于可选改造栏。
- `ThunderThrowV1/` 作者脚本保留为历史来源；其旧模型和旧图标发布流程不用于本轮重建。后续维护以此目录和 `FactoryIconsV2` 为准。

本轮通过现有 UE 桥导入与保存，未启动、关闭或重启编辑器。没有运行游戏测试或额外验收；玩法、伤害、动画和改造 ID 均沿用已有实现。
