# 门族扩展与遗留修复（2026-10-04）

上一轮门系统审计（见对话记录）定级 2/3/4/5 四项待办，本轮全部处理。**未实机测试，由用户验收。**

## 项 4：两侧皆堵拒绝开门 + 开关门静音（用户拍板）

- `AColdSteelDoor::OpenDoorFrom` / `AColdSteelWindow::OpenWindowFrom`（双开门继承）改为**返回 bool**：
  首选侧被挡仍反向开（原口径保留）；**两侧摆动空间都被实体挡住时拒绝开门**（原先"宁可夹着开/穿墙"），
  日志记 `两侧摆动空间均被阻挡，拒绝开门`。玩家/Pawn 不参与阻挡判定（IsSwingBlocked 原口径不变）。
- 撞门链路 `AdvanceAuthority` 使用返回值：被拒 → `ClientPushResult(false)`，本地动作取消、不播撞击音。
- **开关门不播顶部提示栏**：核查 E 键门路径（`FPSGAMEPlayerController.cpp` 门分支注释"开关门保持安静"，
  b14fd662 已不把 OutMessage 送提示栏）、撞门链路、自动关门路径——均无提示栏调用；本轮新增路径同样静音。
  准星小浮窗的提示文案保留（那不是提示栏），并按门种细分（见下）。

## 项 2+3：铁门透缝 + 铁门联机

`door_physics` 调色板条目的 ActorClass 从 Fab 物理门 `BP_PhysicsDoor_C` 换为**原生子类
`AColdSteelContactDoor`**（`Building/ColdSteelContactDoor.h/.cpp`）：

- 网格换本工程补缝门框/门扇（SM_SingleDoorFrame_D40 族）——透缝随铁门并入原生门族一并消除；
- 开合走 `AColdSteelDoor` 的服务器权威链路与开合复制——远端玩家可见（原物理门不复制）；
- "撞开"语义 = 门口薄触发盒（30×60×120 半尺寸，X 两侧各多 10cm）在**服务器**上检测**玩家**走入
  即开门；怪物撞门不开（守家口径）；E 键照常可开关；
- 两边皆堵时同样拒绝开门（项 4 口径）。

旧 `BP_PhysicsDoor` 资产留在 `Content/DoorSystem/` 不再被调色板引用。

## 项 5：迁移了但停用的包功能 → 原生等效实现

包内四类门 BP 依赖包自己的第三人称角色与输入（OnInteraction Cast 到 BP_ThirdPersonCharacter 会失败，
2026-09-17 实测），统一改为**原生实现**（全部进 `IsNativeDoor` 门族：E 服务器权威、开合复制、
建造调色板可放置、存档重生成）：

| 调色板条目 | 类 | 语义 |
| --- | --- | --- |
| `door_key` | `AColdSteelKeyDoor` | 上锁的门：E 时校验操作者钥匙环，有钥匙→解锁（会话内保持）并开门；无钥匙→拒绝。撞门链路同样被拒。准星提示显示锁况 |
| `key_pickup` | `AColdSteelKeyPickup` | 门钥匙拾取物：走入触发范围登记钥匙（`AFPSGAMECharacter::GrantDoorKey`，会话内有效、不进存档）后消失。外观=引擎基本体拼的小钥匙（悬空慢转），后续可换网格 |
| `door_slide` | `AColdSteelSlidingDoor` | 双扇对滑：门扇沿框平面各滑 52cm 让出通道；滑动路径被实体挡住→拒绝开门；6 秒自动关。NetSwing 的 From/To 存滑动偏移 cm |
| `door_drag` | `AColdSteelDragDoor` | 拖拽门：按住 E 持续摆动（闭→全开 / 开→回关），松手在当前角度冻结（可停任意开角，不自动关）。松手经 `UFPSDoorPushComponent::ReleasePressedDoor`→`ServerReleaseDoor` RPC |
| `door_revolving` | `AColdSteelRevolvingDoor` | 三扇旋转门：E 或玩家走进门口即旋转 120°（方向随操作者所在侧）；转动中对 Pawn 放行、停稳后挡人；中柱=引擎基本体 |

包 BP（BP_KeyDoor/AutoClose、BP_DragDoor、BP_RotatingDoor(s)、BP_SlidingDoors、BP_WrongSideDoor）
继续留在 `Content/DoorSystem/` 不再使用。**注意**：键门/钥匙的解锁状态为会话级（跨运行重置）；
若日后要跨存档持久化，需要单独的存档迁移规划。

## 接线改动

- `AColdSteelDoor`：`OpenDoorFrom`/`ToggleDoorFrom`/`ReleaseDoor` 虚化，开合机制段 private→protected（门族子类共享）。
- `UFPSDoorPushComponent`：新增 `static IsNativeDoor(AActor*)`（门族判定，含新四类）与
  `ReleasePressedDoor`/`ServerReleaseDoor`（拖拽门松手 RPC）；`RequestDoorInteraction`/`ServerCanInteract`
  /`ServerToggleDoor` 改走 `IsNativeDoor` 并扩展四类分派。
- `UColdSteelDoorInteraction::TryInteract`：原生门族判定改 `IsNativeDoor`（滑动/旋转门不再落包门泛化路径）。
- `ColdSteelWorldInteraction::ResolveInteractionHint`：准星提示按门种细分（键门锁况/拖拽/铁门/普通门）。
- `AVoxelBuildWorld::SpawnPrefab`：滑动/旋转门的材质配置接入。
- 调色板（`Rounded/DA_VoxelBuildPalette`）经 commandlet 登记（`Tools/AssetPipeline/register_door_prefabs_20261004.py`），
  现门族条目 12 条；`door_physics` 缩略图换补缝门扇。

## 构建

Game（31.9s）与 Editor（并行会话 11:29 构建，DLL 内已核验六个新类符号）双目标 Succeeded。
调色板 commandlet 回执 save=True、DOOR_IDS 12 条。**未实机测试**：新门放置/开锁/拖拽/旋转/滑动的
手感、联机复制、自动关与挡人恢复，均由用户进游戏验收。
