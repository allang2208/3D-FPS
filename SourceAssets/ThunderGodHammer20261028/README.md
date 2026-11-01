# 雷神之锤制作源

用户提供的 `Meshy_AI_Stormbreaker_Runehamm_1028015020_texture.glb` 按现有双手锤流程制作。最终输入是 `Original/` 中的 GLB；`ConceptV1..V4` 是之前的设计迭代，不覆盖本次模型的形状和贴图。

- 武器 ID：`ue_thunder_god_hammer`；显示名：雷神之锤。
- UE 根目录：`/Game/Weapons/ThunderGodHammer20261028`。
- 总长 115 cm，锤头宽约 34.14 cm、厚约 11.81 cm。握区、柄颈和接口适配现有 WPN_root 双手锤坐标与动作。
- 原 GLB 为 218,018 顶点、392,646 三角形；保留原始密度、UV 与法线，模块切口补面会增加三角形。
- 使用原生 BaseColor、MetallicRoughness、Normal。输入无发光通道；蓝色刻纹保留原贴图，不增加固有雷击或雷电特效。
- 原装六模块：中座、成对锤头、颈部、长柄、握柄、尾锤。枪匠五栏：锤头、中座、符文、握柄、尾锤。
- 已制作 16 件适配接口的通用配件：4 锤头、5 中座、3 握柄、4 尾部选项。包括破势古印座、鸣雷疾驱座及无尾锤；附加符文复用现有 5 种通用符文。
- 第一、第三人称动作通过 `tool_kind=warhammer` 共享；不复制动作资源，不覆盖现有玩家动作配置。
- 数值独立登记，初值沿用当前钢制战锤的力量／体质公式。新旧玩家由现有初始军械库流程按定义 ID 幂等发放。

## 制作入口

1. Blender 后台运行 `author.py`：源模型归档、PBR 提取、握持比例适配、整模 FBX。
2. Blender 后台运行 `ModulesV1/author_factory.py`、`author_adapted.py`、`author_icons.py`：原装切分、通用接口适配、枪匠实际模型图标。
3. `build_game.ps1` 和 `build_editor.ps1`：必要构建；不启动编辑器界面。
4. `run_assets.ps1 -Stage base`、`-Stage modules`：新增资产导入与保存。
5. `python register.py`：本武器条目、独立公式、模块表、枪匠表和烹饪目录登记。
6. `run_inventory.ps1`：通过现有原生库存图标 commandlet 生成本武器图标。
7. `run_assets.ps1 -Stage icon`：保存背包 Texture2D。枪匠图标按既有约定直接使用暂存 PNG。
8. `python record_delivery.py`：整理制作回执和共享动画清单。

UE 资产与图标生产使用现有 `Local\CodexUeMcp-Port-8000` 批次互斥。脚本保留已有资产，不作为日后重导工具使用；修改本武器时应明确安排重导版本。`Before/` 仅记录本次修改前的文件，禁止覆盖恢复整个共享文件。

## 交付记录

制作与保存结果见 `delivery.json`、各阶段 `*_receipt.json` 和 `ModulesV1/import_receipt.json`；共享动作映射见 `animation_manifest.json`。本次仅制作、导入、登记及必要构建；未运行游戏、自测或验收，交由用户测试。

随后用户明确要求复查，结果保存于 `Review20261028/review.md` 与 `summary.json`。该轮补齐鸣雷疾驱座电弧的模型识别、通用符文的长柄材质识别和材质实例复用；此前制作阶段的 `tested: false` 是当时状态，复查记录单独保留。
