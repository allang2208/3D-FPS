# 焚化厅负一层：全幅大开间调整

> 用户已基本认可本版布局；灯光随后由 [废弃医院灯光调整](dungeon-incinerator-morgue-lighting-20260930.md) 接续，以下九灯亮度属于布局初版记录。

> 地下墙面与地面已接续 [医院模板随机血迹](dungeon-incinerator-morgue-blood-20260930.md)，随每次进入重新分布。

按用户的两张现场截图调整原停尸房。此版取代 [B1 初版布局](dungeon-incinerator-morgue-b1-20260930.md)，继续使用「废弃焚化处理厅 · 主体样板」地图。

## 布局

- 地下层沿用楼上七边形主体轮廓，最大宽深 28 × 21 m，外轮廓面积约 565.5 m²。地面标高仍为 -3.6 m，楼板底 -0.25 m；范围包含楼梯和两间功能房。
- 拆掉折返楼梯中间的实墙、出口墙及侧面围护墙。两跑楼梯改成有厚度的梯板，下方与两跑之间开放；转台补充侧边与后侧栏杆。保留既有楼板开口、每跑 12 级、15 cm 踏步高和 1.8 m 梯宽。
- 取消原转运前室隔墙，下楼直接进入连续大厅。登记桌和一台转运车位于西侧；另一台转运车靠近东侧冷藏柜，中央留作作业和通行空间。
- 12 仓端开门遗体冷藏柜移至东墙，保留原第 08 仓展开的空托盘。
- 仅保留北侧两间封闭功能房：整理清洗间和制冷设备间，各约 6.8 × 5.16 m。整理台和清洗槽随房间移动；主要设备沿用现有资产。
- 接灰装置继续位于楼上右侧炉旁。上层既有地面划线、炉体、观察台和家具位置沿用现有版本。

## 门框接缝

初版门洞的墙端、瓷砖端和门框内侧面处在相同平面。此版将墙体洞口与门楣退入门框 6 mm，门框改为连续 U 形网格，避免三段方管端面重叠。框体深 28 cm，覆盖 20 cm 隔墙及两侧瓷砖，外表面留出层次。

原前室和楼梯出口的门框随隔墙移除。北侧两间房使用新门框；原封闭转运双门移至西墙，其门板与墙面留有间距。方向牌、冷藏柜编号和房间牌随布局调整，墙面牌的背板与墙面留 2 mm 安装间距。

## 制作与接入

源目录：`SourceAssets/DungeonIncineratorHall20260929/MorgueOpenPlan20260930/`。

- `Config/layout.json`：此版轮廓、分区、设备与灯位。
- `Scripts/prepare.py`：从既有设备布局生成新配置。
- `Scripts/author_architecture.py`：房壳、楼梯、门框、结构与吊架。
- `Scripts/author_signs.py`：标识搬移与转台护栏；保留原上层栏杆。
- `Authored/Architecture/Morgue_OpenPlan_B1_ArchitectureV2.blend`：建筑及楼梯源。
- `Authored/Morgue_OpenPlan_SignsV2.blend`：标牌及栏杆源。
- `Scripts/install_morgue.py`：新包导入、替换所属 B1 Actor、搬移既有设备并保存地图。
- UE 新资产目录：`/Game/Dungeons/IncineratorHall20260929/MorgueOpenPlanV2/`。
- 目标地图：`/Game/GameMaps/Design/L_AbandonedIncineratorHall_Subject`。

主重建配置及其生成脚本已指向本版。旧 B1 资产保留，设备继续引用旧版已保存网格；本版另存 8 个建筑网格、栏杆和标牌网格，以及 2 张标牌纹理和 4 个材质。照明按新范围分布为 9 盏，其中 4 盏投影，保留局部照明方式。

本批后台导入与地图保存已完成，commandlet 退出码为 0；`Receipts/install.json` 记录 `stage=morgue_open_plan_v2_saved`、`map_saved=true`。原地图保存前副本位于本批 `Backup/`，新 Blender 源、FBX 和 UE 资产均已落盘。

遵照用户要求，不启动游戏，不进行 PIE、截图、渲染或测试；楼梯通行、光照和门框闪动的实机结果由用户确认。
