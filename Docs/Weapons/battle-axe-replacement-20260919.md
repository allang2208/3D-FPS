# 伐木斧模型替换：Meshy 风化战斧（2026-09-19）

将 `tool_axe`（伐木斧）的模型替换为用户提供的 Meshy 风化战斧。世界掉落/拾取、第一人称手持、背包图标三条呈现同时更新；物品 ID、采集次数、产出、时序、声音和存档身份不变。

## 来源与输入

- 用户提供：`D:/FPS3D/资产/Meshy_AI_Weathered_Battle_Axe_0918025738_texture_fbx.zip`
- 内容：46 万三角面单连通块高模 + 4 张 2048² 贴图（BaseColor / Normal / Metallic / Roughness）。
- ZIP 里的 FBX 自带材质引用了不存在的 `.fbm` 贴图目录，已改用包内 PNG 重新绑定。
- 源包与派生物留本机；本任务目录 `SourceAssets/BattleAxeReplace20260919/`。

## 与旧斧头的差异（决定了适配步骤）

| 项目 | 旧斧（FreeFab） | 新斧（Meshy） |
| --- | --- | --- |
| 面数 | 1,728 | 460,716 |
| 刃朝向 | +X | **-X（需转 180°）** |
| 贴图 | 4 张 1024²，无金属度贴图（顶点色遮罩代替） | 4 张 2048²，含真实金属度 |
| 法线 | 项目既有 | OpenGL 约定，**需翻绿通道** |

## 适配与档位

`SourceAssets/BattleAxeReplace20260919/fit_battle_axe.py` 完成：烘焙导入变换 → 绕 Z 转 180°（对齐旧刃向）→ 缩放到 78 cm → 包围盒居中（沿用原居中 Z-up 枢轴）→ Collapse 减面 → 平滑着色导出。

- **世界网格**：16,000 面 + 2 级 LOD（2,500 / 600），屏幕尺寸 1.0 / 0.35 / 0.1。
- **第一人称视模**：32,000 面。近景能看到绳缠纹理；8,000 面档的绳纹已明显融化，故不采用。
- 减面质量对比渲染在 `DecimateCheck/`，档位选择理由见该目录。

## 视模重建

`rebuild_battle_axe_viewmodel.py` 从已认可的作者源 `ProductionToolGrip20260913/Axe_SingleHand_Editable.blend` 出发，**只替换工具网格**，保留骨架（100 骨）、双臂、五条动作（Idle/Walk/Equip/Swing/HitRecover）和抓握关系。

- 握点 `grip_z = -0.26 m`：与原斧头在同一杠杆位置，手落在绳缠握区。候选位 -0.10 / -0.17 / -0.20 / -0.24 / -0.26 均有渲染对比（`GripZoom/`、`GameView/`），最终按"保持已验收的挥动杠杆"选定。
- 游戏口径预览（垂直 75° FOV、视模在相机右 7 cm 下 7 cm）见 `render_game_view.py`。

## UE 安装

`Tools/Production/install_battle_axe.py`，经编辑器内远程通道执行（资产被编辑器加载时，外部进程保存会静默失败）：

- 新资产：`/Game/Items/ProductionTools/BattleAxe20260919/`
  - `SM_BattleAxe`（16k + 2 LOD，Nanite 关闭，自动碰撞）、`M_BattleAxe`、4 张贴图。
  - 贴图：BaseColor sRGB；Normal `TC_NORMALMAP` + `flip_green_channel=True`（Meshy OpenGL 约定）；Metallic / Roughness `TC_MASKS`，全部 2048 上限、常规 mip 流送。
- 视模：`/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe` 重新导入，槽位按**槽名**绑定 —— `M_Harvest_Axe` 槽改指 `M_BattleAxe`（新贴图），`MI_Manny_01/02` 保持当前 M4 手臂材质。
- **顺带修复既有缺陷**：`SK_Harvest_Axe_Skeleton` 自 2026-09-13 首次导入起从未保存到磁盘，视模与五条动作一直引用悬空骨架（导入日志确认当时没有保存该包；未改动的矿镐同样如此）。本次保存了骨架资产（101 骨），新进程读回确认视模与 `A_Harvest_Axe_Idle` 都能解析到它。
- 旧资产全部保留在原地：`SM_Free_Axe`、`M_FreeAxe`、`M_Harvest_Axe` 继续存在，可随时切回。

## 引用切换

- `Content/ColdSteelData/production_tools.json`：`tool_axe.tool_mesh` → `SM_BattleAxe`。物品 ID、viewmodel、动作前缀、声音、时序、缩放与持握旋转均未改动。
- `Config/DefaultGame.ini`：新增 `DirectoriesToAlwaysCook=/Game/Items/ProductionTools/BattleAxe20260919`；旧 Axe 目录保留。

旧存档无需处理：`NormalizeProductionState` 在载入时按白名单把 `tool_mesh` 等外观字段刷新为定义值，物品身份、数量、位置和采集进度不受影响。

## 图标

`SourceAssets/BattleAxeReplace20260919/render_icon.py` 用包内真实 PBR 贴图渲染 512² RGBA 透明 PNG，构图沿用旧图标（斧头朝右上、柄朝左下、无地面无文字）。已替换 `Content/ColdSteelData/ProductionTools/axe.png`，变更前副本在 `Before/ProductionTools_axe.png`。

## 验收记录

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| 导入 | 8 个资产保存成功、0 错误 | `Saved/Logs/BattleAxe-install.log` |
| 新进程读回 | 骨架解析、视模槽、三角形数、LOD 全部正常 | `readback.json`、`Saved/Logs/BattleAxe-verify2.log` |
| 世界网格尺寸 | 高 78.0 cm、宽 23.1 cm | 远程通道读回 |
| 骨架层级一致性 | 新旧 FBX 100 骨名称与父级全同 | `bone-compare.json` |
| 图标 | 512² RGBA，运行时直接加载可用 | 远程通道读回文件 |
| 游戏内表现 | **未测试**，由用户验收 | — |

本次未改动任何 C++ 源文件，不需要重新编译。渲染图（Blender 出品）只用于制作判读与档位选择，不代表引擎内观感验收。

## 重建入口

1. `fit_battle_axe.py` —— 源 FBX → 适配 + 减面（世界 16k / 视模 32k / LOD1 2.5k / LOD2 600）。
2. `rebuild_battle_axe_viewmodel.py` —— 作者源 blend → 换工具几何 → 视模 FBX + 新可编辑 blend。
3. `Tools/Production/install_battle_axe.py` —— UE 导入与引用绑定。
4. `Tools/Production/verify_battle_axe.py` —— 新进程回读验收。
5. `render_icon.py` —— 背包图标。

输入依赖：原始 ZIP（本机）、`ProductionToolGrip20260913` 作者源与 `MannyGraspDonor20260912` 抓握母版、`Tools/Production/build_tool_grip_motion.py`。