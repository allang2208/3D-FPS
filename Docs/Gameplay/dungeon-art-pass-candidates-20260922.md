# 地牢美术资产：场景盘点与可商用候选（2026-09-22）

用户要求：看新构建的地牢场景，找**贴合场景且许可可商用**的美术资产。
本轮只做**盘点与筛选**，未下载、未导入、未摆放。可执行清单见 [`Config/shortlist.json`](../../SourceAssets/DungeonArtPass20260922/Config/shortlist.json)。

## 1. 场景现状（依据截图 + 文档 + 9/22 的 Actor 扫描）

地图 `/Game/GameMaps/L_Dungeon_AuthoredExpansion`，共 **225 个 Actor**：

| 区段 | 内容 |
| --- | --- |
| A 段原样板（164 Actor） | 走廊、低顶工作间、格栅设备区、检修壁龛、**遗迹侧穴（石拱 + 基座，旧雕像已退役留下空拱）**、折角、末端平台 |
| 检修连接通道 | 2 件定制开口网格 |
| 管线分配间 / 排水检修室 / 破损支护室 | 34 件建筑网格 + 12 处灯具 + 10 个隐藏锚点 |

观感与既有材质：混凝土墙 + 象牙陶瓷墙裙、顶面管道与电缆桥架、荧光灯管、钢丝网格栅与设备笼、石拱 + 基座 + 破口 + 碎砖、潮湿贴花。**写实、低饱和、冷暖分区（冷白可读性 + 琥珀事件焦点）**。

### 缺口

**场景里几乎没有散件。** 164 个 A 段 Actor 全是结构件、管道、栅栏与灯具；三个新房间按设计是"纯建筑壳 + 隐藏锚点"（文档原话：*10 个隐藏锚点用于后续放置玩法和美术，场景内不放占位道具盒*）。

这与既有 [`dungeon-room-asset-list`](dungeon-room-asset-list-20260920.md) 的缺口完全一致——清单 E1–E13（木桶／木箱／骨堆／铁链／蛛网／破布／木架／长凳／梯子／火把托架／贴花）与 D2–D5（灯架／火盆／蜡烛／光晕）**全部标注为「新建」且尚未制作**。

## 2. 筛选口径

- **渠道**：Sketchfab Data API v3，`downloadable=true`，`license=cc0|by`（只要可商用）。
- **规模**：42 个检索词，786 个候选（CC-BY 754 / CC0 32），人工看图标筛 46 件。
- **贴合判断**：写实扫描或写实 PBR；色调能被现有材质吸收；不与项目已精确建模的构件重复。
- **许可判断**：CC0 优先（无需署名），CC-BY 次之（必须署名，接入时写 `ThirdPartyNotices`）。**CC-BY-NC 一律不取**。

## 3. 推荐清单

### A 组｜工业散件（走廊、工作间、检修壁龛、三个新房间）

| 资产 | 许可 | 面数 | 用在哪 |
| --- | --- | --- | --- |
| Fire Extinguisher Old Rusty 3D Scan | CC BY | 30.0k | 走廊／维修凹室挂墙——真实扫描，锈蚀自带 |
| Old Rusted Bucket v3 | CC BY | 2.9k | 工作间地面 |
| Rusty and Oil Stained Oil Barrel | CC BY | 812 | 设备区、排水检修室 |
| Old Ammo Crate | CC BY | 1.1k | 工作间、补给点 |
| Low Poly \| Pallets | CC BY | 1.8k | 管线分配间地面 |
| Cable Spool | CC BY | 1.7k | 分配间／维修间 |
| Game Ready Jerry Cans | CC BY | 4.7k | 维修间 |
| Crushed rusty oil drum | CC BY | 187k | 废料堆——**偏重，建议先减面** |

### B 组｜遗迹石作与器物（遗迹侧穴、破损支护室石质空腔）

| 资产 | 许可 | 面数 | 用在哪 |
| --- | --- | --- | --- |
| Broken ancient greek column - debris | CC BY | 84.9k | 破口与空腔地面，与已有石拱同源风格 |
| Broken Medieval column set | CC BY | 4.7k | 空腔角落 |
| **1970.16 Neck Amphora** | **CC0** | 113k | 石拱前供奉（无需署名） |
| **Queen Jadwiga's sarcophagus** | **CC0** | 128k | 空腔焦点／祭台（无需署名；体量大，需核对 4×5 m 空腔与 3.35 m 净高） |
| Red Sandstone Winged Lion Corbel | CC BY | 7.9k | 墙头嵌件 |

### C 组｜氛围小件（全场景点缀，性价比最高）

| 资产 | 许可 | 面数 | 用在哪 |
| --- | --- | --- | --- |
| **Cobwebs Asset Pack** | CC BY | 419 | 顶角／门框／破口——2223 likes，alpha 卡，几乎零成本 |
| Lowpoly Animal Skulls - 1 | CC BY | 87.5k | 骨堆与仪式痕迹（整包 69 张贴图，按需取件） |
| Low Poly Bone Pile | CC BY | 560 | 地面小堆 |
| Antique Candle Holder | CC BY | 2.9k | 遗迹祭台（对应清单 D4 蜡烛组） |
| Rusty Old Oil Lantern | CC BY | 7.6k | 遗迹与暗角 |
| Burlap Sack / Grain Sack | CC BY | 4.6k / 3.3k | 补给堆（对应 E7） |
| Wooden Step Ladder Scan LOWPOLY | CC BY | 824 | 工作间（对应 E10） |
| Rusty metal grate | CC BY | 678 | 排水检修室槽盖 |
| Coiled Rope 2 | CC BY | 20.0k | 分配间／维修间（对应 E5 类） |

### D 组｜灯光一致性

| 资产 | 许可 | 面数 | 说明 |
| --- | --- | --- | --- |
| Industrial Hanging Ceiling Lights Type B | CC BY | 37.1k | 大空间吊灯；若要补灯，优先与走廊现有荧光灯管同型，避免照明语言分裂 |

### 额外：CC0 贴图／环境源（无需署名）

**ambientCG** 与 **Poly Haven** 全站 CC0：混凝土、锈蚀、瓷砖、污渍、法线与粗糙度可直接取用。对"把现有墙地做得更脏更旧"这类需求，比下载一堆网格更划算。

## 4. 明确**不建议下载**的部分

- **规则构件**：法兰、支架、电缆桥架、格栅、门五金、灯壳、仪表、电柜——继续本地精确建模。项目已有 `SM_MaintenanceCabinet`（含 DIN 导轨、断路器、铜排、铭牌）这类先例，下载包只会与现有构件撞风格；`asset-model-workflow` 的形态分流也要求规则件走精确建模。
- **风格化／低模包**：如 689 likes 的 `Ancient Ruins`（带绿植的低模场景）、PS1 风格包——与本场景写实方向冲突。
- **带植物的园林件**：`Garden Urn`（花是错的语义）。
- **含人物的场景件**：`Roman Pottery workshop`（是人物工作场景，不是道具）。
- **已有同类不再买**：碎砖／瓦砾（已有 `Ind_Con_Pile_Rubble_Gravel_Patch_01`、`Mil_Trench_Debris_*`）、石拱（已自建）、瓷砖墙。

## 5. 许可与合规

- 上述 22 件里 **2 件 CC0**（陶瓶、石棺）无需署名；**其余 20 件为 CC BY 4.0**，接入时必须署名。
- 建议：正式接入时新建 `ThirdPartyNotices/DUNGEON_ART_PASS.md`，逐件记录标题、作者、页面链接与许可，与已有的 [GODDESS_STATUE.md](../../ThirdPartyNotices/GODDESS_STATUE.md)、[STATUE_SET.md](../../ThirdPartyNotices/STATUE_SET.md) 同规格。
- 一律排除 CC-BY-NC / NC-SA / ND / Editorial：不可商用或不可再分发。

## 6. 边界与下一步

- 本轮**未下载、未导入、未摆放**任何一件；上表仅为筛选结果。
- 场景透视盘点（`Scripts/inventory_map.py`）本轮**未跑成**：另一会话的编辑器（巫婆任务，`L_Dungeon_Randomized`）长时间占用，脚本按不打扰他人会话的规则拒绝起第二个进程，也没有切换对方关卡。缺口结论来自 9/21 截图、9/22 房间文档与 9/22 的 Actor 扫描回执（225 Actor）。
- 若用户点头，建议顺序：先 C 组（零成本、立刻改善观感）→ A 组（工业叙事）→ B 组（遗迹焦点）→ D 组（照明统一）；每件按 Diana / 塑像套件同一套管线（代理下载 → Blender 归一化 → FBX → UE 导入 → 独立读回）。
