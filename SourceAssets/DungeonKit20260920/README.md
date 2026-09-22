# 地牢原型关卡（现有构件搭建）

日期：2026-09-20 · 宿主：`D:/FPS3D/FPSGAME`（UE 5.8.2）
关卡：`/Game/GameMaps/L_Dungeon_Prototype`
配套：[地牢迁移实施方案](../../Docs/Gameplay/dungeon-migration-plan-20260920.md) · [单房美术资产清单](../../Docs/Gameplay/dungeon-room-asset-list-20260920.md)
范围：**只用工程现有构件**搭出的可玩原型，验证布局、尺寸、拼接与上下楼。不涉及地形破坏、不涉及 20 cm 体素建造、不涉及 5080 新道具（那批在 `SourceAssets/DungeonProps20260920` 另行推进）。

## 1. 用了什么构件

全部来自工程已有资产，没有新建几何：

| 用途 | 资产 | 实测尺寸（cm） |
| --- | --- | --- |
| 墙 | `/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/SM_Polygonal_Stone_Wall` | 300 × 18 × 300 |
| 地板（基座板） | 同目录 `SM_Polygonal_Stone_Foundation` | 300 × 300 × 170（下沉 85 后顶面即楼层地面） |
| 天花板 | 同目录 `SM_Polygonal_Stone_Ceiling` | 300 × 297 × 10 |
| 楼梯 | 同目录 `SM_Polygonal_Stone_Stairs` | 302 × 309 × 307（抬升一层） |
| 门框（门洞） | 同目录 `SM_Polygonal_Stone_Doorframe` | 300 × 28 × 300（洞口在内部） |
| 圆柱 | `/Game/Props/RomanColumn20260915/SM_RomanColumn_Round_20` | Ø90 × 260 |
| 木桶 | `.../Ind_Storage_Barrel_Metal_Rust_01/...` | Ø59 × 85 |
| 长凳 | `.../Mil_Trench_Bench_Wood_01/...` | 252 × 60 × 72 |
| 碎石 | `.../Ind_Con_Pile_Rubble_Gravel_Patch_01/...` | 267 × 223 × 23 |

**关键发现：EBS 是 300 cm 模组**（不是 200），所以地牢网格按 300 cm 走。门框洞口是构件自带尺寸，约 200 宽 × 240 高量级——与方案 §5.1 要求的"净 200×240"同档，**但洞口实际数值需要实测确认**（本次未量）。

### 1.1 垂直结构（2026-09-20 修复后）

三件构件的高度不同，必须先算清再搭，否则玩家会和楼板打架：

| 构件 | 厚度 | 放置点 → 实际跨度 |
| --- | --- | --- |
| 地板 `Foundation` | 170 | 放置 z-85 中心：跨 z-170 … z（顶面 = z） |
| 天花板 `Ceiling` | 9.6 | 放置点即顶面参考：跨 p-2.1 … p+7.5（**顶面 = p+7.5**） |
| 墙 | 300 | 放置 z+150 中心：跨 z … z+300 |

**规则**：
- **一楼地板**用厚基座（下沉 85，顶面 = 0）。
- **二楼楼面**用薄天花板件，**放置点 = 300**（顶面 = 307.5）。二楼房间若下方同格已有一楼天花板（`over_ceiling=True`），就**不再铺**——两层薄板重叠会 z-fighting。只有楼梯间上方（楼梯间不封顶）才自铺。
- **二楼顶盖**放在 300+300=600，顶面 607.5。
- 实测净高：**一楼 297.6 cm、二楼 290.4 cm**（玩家胶囊 192 cm，余量充足）。

**这一版踩过的坑**（第一版把二楼也铺了厚基座）：基座下沉 85 → 底面在 130，侵入一楼 170 cm，一楼净高只剩 130 cm，出生点胶囊（6…198）与楼板（130…300）重叠 68 cm，角色被挤压穿地——这就是"进地牢掉到地下"的根因之一。

## 2. 关卡布局

网格单位 300 cm，两层，共 7 个房间：

```
二楼 z=300   [ Boss 0-3 ][ corridor1 4-5 ][ landing1 6-7 ]   ← 楼梯口在 landing 的 7,1
一楼 z=0     [ entry 0-1 ][ corridor0 2-3 ][ combat 4-5 ][ stairs0 6-7 ]  ← 楼梯在此，无天花板
                     ← ── X 轴（东向）── →
```

- 每层 8×2 格 = 24 × 6 m；房间 6×6 / 12×6 m，走廊 6×6 m。
- 门洞位置：entry↔corridor0、corridor0↔combat、combat↔stairs0（各 1 个，均在 Y=0 行）；
  二楼 landing1↔corridor1、corridor1↔boss。
- **边界只建一次**：相邻房间的共享边先收集再按"门优先于墙"去重，避免两面墙重叠 z-fighting。
- 房间格子有重叠检测：同一格被两个房间认领会直接报错（第二轮就是这样发现 Boss 房与走廊撞格的）。
- 楼梯间不封天花板，二楼 landing 的楼梯格不铺地板——洞口对齐，从一楼能爬上去。

## 3. 灯光与运行

- 全部光源 **Movable**：方向光 + 天光 + 天空大气 + 体积雾 + 4 个点光（每主要房间一个），无需构建光照即可看。
- 关卡 GameMode 设为 `FPSGAMEGameMode`，PlayerStart 在入口房中央附近 (450, 450, 20)。
- 全部 Actor 归入 `DungeonPrototype` 目录，重跑脚本会先清空该目录再重建，不会重复堆叠。

## 4. 运行入口

```powershell
# 搭建（无头，不占用交互编辑器）
& "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" `
  D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript `
  -script=D:/FPS3D/FPSGAME/SourceAssets/DungeonKit20260920/build_dungeon_headless.py `
  -unattended -nop4 -nosplash -nullrhi

# 只读核对（不修改关卡）
... -script=.../verify_dungeon.py ...

# 相机预览渲染（commandlet 渲染通道；见 §6 限制）
... -script=.../preview_dungeon.py ... -AllowCommandletRendering
```

脚本：`build_dungeon_headless.py`（搭建）、`verify_dungeon.py`（核对）、`preview_dungeon.py`（机位渲染）、`audit_kit.py`（构件尺寸盘点）、`portal_geometry_check.py`（门位几何核对）。

## 4.1 传送门接入（2026-09-20）

`Source/FPSGAME/SceneTestPortal.cpp` 改动三处，已随 `Build-Editor.ps1` 编译通过：

| 位置 | 改动 |
| --- | --- |
| `ScenePortalMaps` 命名空间 | 新增 `Dungeon = /Game/GameMaps/L_Dungeon_Prototype` |
| `OnWorldBeginPlay` 地图白名单 | 加入 `L_Dungeon_Prototype` |
| `SpawnPortals` 目的地列表 | 主城新增「DUNGEON / Prototype」门（橙黄）；地牢内只生成一扇「HOME / Main Map」门（浅蓝） |

**出生点前移**：传送门子系统把门放在玩家前方 350 cm 处。原出生点 x=450 会让出口门穿进入口房与走廊之间的实墙（墙线 x=600，门位 x=800 且落在无门洞的 j=1 段）。出生点改到 x=150 后，门位 x=500 落在入口房内。

**几何核对**（`portal_geometry_check.py`，commandlet 无物理场景，故按放置公式算而非射线探测）：

| 关卡 | 门 | 位置 | 结果 |
| --- | --- | --- | --- |
| L_Dungeon_Prototype | HOME / Main Map | (500, 450) | 落在 `entry` 房内 ✅ |
| DayNight_Lighting | DUNGEON (new) | (350, 220) | 与另三扇门等距 440 cm 排列 ✅ |

**未验证**：门是否浮空/埋地需要实机确认——门位 Z 由下落射线决定（找不到地面时回退 −90 cm），这条只有真实物理场景才成立。主城出生点 Z=102、朝向 yaw 0，四扇门共占 1320 cm 横向跨度，需实机确认没有家具或地形阻挡。

## 4.2 「进地牢掉入地下」排查与修复（2026-09-20）

**现象**：走传送门进地牢后直接掉到地下。

**三个根因，全部已修**：

| # | 根因 | 证据 | 修法 |
| --- | --- | --- | --- |
| 1 | 出生点 Z=20 太低 | 胶囊半高 96 → 出生时脚底在 −76，嵌进地板（顶面 0）；主城标准是 **102** | `DungeonStart` 改为 **Z=102**（脚底 6 cm，余量 5.6 cm） |
| 2 | **二楼误用 170 cm 厚基座当楼板** | 下沉 85 → 底面 130，一楼净高只剩 130 cm；玩家胶囊 6…198 与楼板 130…300 重叠 68 cm → 被挤压穿地 | 二楼改用薄天花板件（放置点=300，顶面=307.5）；一楼净高恢复到 **297.6 cm** |
| 3 | 地牢不在 GameMode 安全出生白名单 | 走 `Super::RestartPlayer()`，没有安全检查补偿 | **有意保持不在白名单**：`FindSafeSpawn` 从 PlayerStart +500 cm 探测，该点落在二楼顶盖内部（597.9…607.5），所有探测被 `bStartPenetrating` 拒绝 → 加了反而完全生不出角色。已在源码注释中写明原因 |

**修复后核对数据**：

| 项 | 值 | 判定 |
| --- | --- | --- |
| 出生点 | (150, 450, 102)，脚底 6.0 | ✅ 与主城同标准 |
| 一楼净高 | 297.6 cm | ✅ 玩家 192 |
| 二楼净高 | 290.4 cm | ✅ |
| 楼梯顶 → 二楼步行面 | 306.7 → 307.5（差 0.8 cm） | ✅ 可连续上楼 |
| Boss 房站立面 | 8 格（继承 entry + corridor0 的天花板） | ✅ 覆盖完整 |
| corridor1 站立面 | 4 格（继承 combat 天花板） | ✅ |
| landing1 自铺楼板 | 3 件 + 1 个楼梯洞 | ✅ 符合设计 |
| 门洞 | 5 | ✅ |

**教训（写给下一位）**：这套构件的"地板"和"天花板"厚度差 17 倍（170 vs 9.6），不能互换用途。**下层用厚基座、上层用薄板**是硬规则；把厚基座放到上层，它会往楼下扎 170 cm。

## 5. 搭建结果（脚本自报 + 只读核对）

| 项 | 值 |
| --- | --- |
| 墙 | 45 |
| 门洞 | 5 |
| 地板 | 31 |
| 天花板 | 28 |
| 楼梯 | 1 |
| 道具 | 8 |
| 点光 | 4（另方向光/天光/大气/雾各 1） |
| 关卡 Actor 总数 | 127（全部在 `DungeonPrototype` 目录） |
| 缺网格 | 0 |
| 楼梯口留空 | 通过 |
| GameMode | `FPSGAMEGameMode`（搭建时写入成功；只读核对返回 None 属 commandlet 读取限制） |

报告文件：`Saved/SceneTests/dungeon-prototype.json`、`Saved/DungeonPreview/shots.json`。

## 6. 已验证 / 未验证

**已验证（脚本断言 + 只读核对）**
- 关卡创建并保存成功；所有网格件均有实际 StaticMesh 引用，无缺失。
- 边界去重生效（第二轮 50 面墙 → 本轮 45 面，重复的共享墙被消除）。
- 楼梯口与二楼地板洞口对齐；楼梯构件存在且朝向与楼层一致。
- 全部件归入专有目录，可安全重跑。

**未验证（按工程规则交由用户实机测试）**
- **没有进游戏、没有 PIE、没有走位测试**：玩家能否顺利穿过门洞、爬楼梯上楼、天花板是否漏光、房间是否封闭，都需要实机确认。
- **commandlet 预览渲染不可用**：`SceneCapture2D` 在 `-run=pythonscript` 下拍不到几何（10 张图逐字节相同，只有天空渐变）。这是无头通道的限制；要看画面请用交互编辑器或游戏内视角。
- 门洞净尺寸没有实测；若与实际怪物体型冲突，需要按方案 §5.1 重新定门。
- 没有碰撞验证（构件自带凸包碰撞，但门洞是否被碰撞堵住未测）。
- 没有灯光观感验收（点是 Movable，参数是占位值 3000/900）。

## 7. 与方案的差异与后续

- 本原型**只验证"能不能用现有资产拼出可走的地牢"**，不含房态机、不含流送、不含 Enemy 波次、不含事件道具。
- 房间尺寸偏大（6×6 m 与 12×6 m）：按方案 §6 修正过的走廊标准（主通道 6–8 m）是对齐的，但战斗房建议后续按 16–24 m 再放大一档。
- 5080 新道具（女神像/恶魔像/遗物/骨堆/破损木箱）到位后可直接替换本原型的占位道具，见 `SourceAssets/DungeonProps20260920`。
- 结构件的**内凹角/外凸角/T字/十字**目前用 EBS 的斜墙与三角件替代验证；正式做异形房时按 [房间形状与全境封锁参考](../../Docs/Gameplay/dungeon-shapes-and-division-reference-20260920.md) 走"格子集合 + 自动砌墙"。