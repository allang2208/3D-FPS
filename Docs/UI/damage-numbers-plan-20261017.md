# 怪物伤害跳字 · 2026-10-17

用户要求优化攻击怪物／训练靶时跳出的伤害数字。当前只有主神空间训练靶通过世界空间 `UTextRenderComponent` 显示数字，效果不佳；本次按用户选择的 B 方案做 MVP：屏幕空间池化伤害数字，先接训练靶，再接普通怪物，自动连发合并为累加数字。

## 目标与范围

- 入口：所有玩家对怪物／训练靶的有效伤害回执；不显示敌方对玩家的伤害，不显示持续伤害跳字。
- 表现：命中点（怪物退化为头顶）投影到屏幕；数字在命中点右上方浮现。
- MVP 档位：普通、重击、暴击／要害、击杀；自动连发和霰弹同目标合并为一条累加数字。
- 保留：训练靶的 DPS 牌、靶面晃动、命中统计和既有靶心暴击判定；HUD 顶部目标条不变。
- 不包含：元素伤害分色、治疗／护盾数字、伤害历史、设置开关；留到后续。

## 当前实现与问题

| 问题 | 当前 |
| --- | --- |
| 贴面遮挡 | [FPSPracticeTarget.cpp](../../Source/FPSGAME/Props/FPSPracticeTarget.cpp) 在命中点 `+4 Z` 生成，未沿相机方向或法线外推；文字平面可能嵌进靶面 |
| 字体/描边 | 默认 TextRender 字体，无描边；亮地面对比不足 |
| 尺寸 | 固定 `WorldSize 15/21`；远小近大 |
| 连发/霰弹 | 每次命中独立 `NewObject + RegisterComponent`，叠成一列；24 条上限 |
| 动画 | 线性上升 48 单位、1.1s、0.65 后淡出；无弹出/档位 |
| 覆盖 | 只有训练靶；普通怪物没有跳字 |
| 联机 | `MulticastPracticeHit` 发给所有客户端，未按攻击者过滤 |
| 性能 | 每个数字创建/销毁组件，高射速下有对象 churn |

## 架构

- 新增 `UColdSteelDamageNumberSubsystem`（GameInstance 子系统）：接收紧凑伤害事件，最多排队 128 条。
- 新增 `UColdSteelDamageNumbers`（HUD 全屏 UUserWidget）：每帧消费事件、合并、投影并绘制；固定池最多 64 条，不按命中创建 UObject。
- 事件字段：目标、观察者 `APlayerController`、世界锚点、伤害、暴击、击杀、重击、是否跟随目标。观察者不匹配的 HUD 丢弃，保证只给实际攻击者显示。
- 数据源：
  - 普通怪物／类人目标：`AFPSGAMECharacter::NotifyConfirmedWeaponHit` 已有实际伤害、暴击和击杀回执；锚点优先取 `head`／`cranium` 骨骼上方 20cm，其次取骨骼网格资产包围盒顶部（不受组件 `BoundsScale` 放大），最后退回全部组件；HUD 每帧重新取锚点，怪物移动或布娃娃后数字仍贴在身体正上方。
  - 训练靶：`OnTakePointDamage/OnRadialDamage/OnAnyDamage` 沿用按帧去重，`RecordHit` 携带 `InstigatedBy`／`DamageCauser` 回退，服务器生成并复制的训练靶把伤害数字通过攻击者 `AFPSGAMEPlayerController::ClientPracticeHit` 回传；锚点用实际命中点，靶面晃动仍对所有客户端生效。
- 联机：只给攻击者本地显示；不新增复制 Actor。
  - 训练靶只在服务器生成并复制，客户端不再本地生成（修复客户端第二个无伤害靶/双靶）。
  - 训练靶伤害数字走攻击者 PC 的 `Client,Unreliable` RPC，不再全服组播后按 `Instigator` 过滤；靶面晃动仍走 `NetMulticast`。
  - 魔法技能把 `Critical`／`Killed` 纳入 `FWeaponDamageResult`，暴击数字和目标条在主机/客机一致；此前魔法技能只传伤害值，暴击样式会丢。
  - 客户端击杀状态使用回执 `bKilled` OR 本地 `Combat->IsDead()`，避免怪物死亡复制延迟时丢「击杀」。
  - 普通怪物沿用已有 owner 回执路径（`ClientWeaponHitFeedback`／`ClientConfirmHit`），标准命中链每条回执一次。

## 显示规则

| 档位 | 颜色 | 字号／缩放 | 附加 |
| --- | --- | --- | --- |
| 普通 | `HUDGoldLight` | 24px；1.0 | 无 |
| 重击 | `DamageHeavy` #FF9A46 | 24px；1.06 | 无标签 |
| 暴击／要害 | `DamageCritical` #FF4D3D | 24px；1.16 | 右侧 12px「暴击」 |
| 击杀 | 沿用命中的档位色 | 同上 | 右侧 12px「击杀」 |
| 连击 | 数字累加 | 同上 | 12px `×N` |

- 字体：数字 JetBrains Mono Medium，标签 Noto Sans SC；全部来自 `ColdSteelUIStyle`，不新增字体资源。
- 描边：数字四向约 1.25px 深色描边，标签单阴影；不加玻璃卡或背景。
- 位置：投影点正上方，数字水平居中、不加横向偏移；数字底边距锚点约 6px。怪物锚点优先取 `head`／`cranium` 骨骼上方 20cm（跟随动画／布娃娃），无头骨时取骨骼网格资产包围盒顶部；训练靶用命中点；视口内 24px 安全边距；锚点出屏则跳过。
- 动画：出生 1.0→1.12→1.0 的短促缩放（约 0.18s）；上浮 36px、ease-out；总时长 1.15s（暴击 1.3s、击杀 1.35s），最后 0.28s 淡出。
- 合并：同目标 0.12s 内新命中累加到现有数字，计数 +1，刷新停留；霰弹一枪一条总伤害，自动连发呈逐渐跳大的数字。
- 同时总计最多 64 条；同目标 0.12s 内合并，未合并的连续动作自然错开；超过时复用最旧条目。

## 数据与状态

| 状态 | 行为 |
| --- | --- |
| 无事件 | 完全隐藏，不占输入 |
| 新命中 | 生成/合并；只在攻击者 HUD 显示 |
| 背包、仓库、商店、工作台、锻造、冶炼、开发抽屉、鼠标模式、弹药／魔法轮盘 | 隐藏并清空当前数字与待处理队列，关闭后不补播 |
| 游戏暂停 | 冻结动画；菜单覆盖时不显示 |
| 读档／HUD 销毁 | 清空临时队列，不写入存档 |
| 目标销毁 | 使用最后一次世界锚点继续淡出 |

## 性能与生命周期

- 一个 HUD 绘制层 + 固定池；不在命中路径创建 UObject/组件。
- 每帧只做世界投影（≤64 条）和文本绘制；文字宽度在生成/合并时测量一次。
- 字体与颜色复用 `ColdSteelUIStyle`；不加载图标、不解析 JSON。
- Construct 绑定 GameInstance 子系统；Destruct 清空队列和条目；面板打开时由 HUD 统一让位。

## 文件范围

- 新增：`Source/FPSGAME/UI/ColdSteelDamageNumberSubsystem.h/.cpp`、`Source/FPSGAME/UI/ColdSteelDamageNumbers.h/.cpp`、`Source/FPSGAME/UI/ColdSteelDamageNumberTypes.h`。
- 修改：`ColdSteelUIStyle.h`（重击/暴击语义色）、`ColdSteelHUDWidget.h/.cpp`（创建与让位）、`FPSGAMECharacterCombatFeedback.cpp`（怪物事件/击杀回执）、`FPSGAMEPlayerController.h/.cpp`（训练靶服务器生成、`ClientPracticeHit`）、`FPSPracticeTarget.h/.cpp`（移除 TextRender 跳字，接入事件）、六个魔法技能回执（暴击/击杀）、`Docs/UI/ui-cold-steel-design-system.md`、`Docs/UI/README.md`。
- 复用：现有伤害回执、目标统计、DPS 牌、靶心判定；无新增贴图、音频或存档字段。

## 联机边界与已知限制

- 训练靶已改为服务器生成/复制 + 攻击者 PC 的 `ClientPracticeHit`；客户端不再本地生成靶。若同类 `SpawnHubTestChest` 仍出现客户端本地副本，需要同样加 `HasAuthority` 门槛（本次未改，避免扩大范围）。
- `ClientPracticeHit` 与 `ClientWeaponHitFeedback` 是 `Unreliable`：丢包时数字可能少一条；伤害/命中判定不受影响。弹道与玩家状态回执走 `ClientConfirmHit`（Reliable）。
- 伤害数字子系统是每个 GameInstance 一份队列，由第一个 HUD 消费；当前单本地玩家成立，分屏/多本地 HUD 不支持。
- 标准命中链（弹道、近战/技能、玩家状态回执）审计为一次回执；若未来新增客户端本地非 cosmetic 投射物同时走本地 `NotifyConfirmedWeaponHit` 和服务端回执，可能出现双数字，需要在新增路径时保持单一回执。
- MVP 仍不做墙体遮挡、不同目标间的轨道错位、元素分色、DoT 跳字、设置开关和独立可靠性队列。

## 构建与测试

- 必要构建：`FPSGAME` 已编译并链接 `FPSGAME.exe`（10:23:32 联机/魔法回执修复；10:27:11 符文刃回执补丁），日志 `Saved/BuildEditor/damage-numbers-mpfix2-20261018-game.log`、`damage-numbers-mpfix3-20261018-game.log`，均 `Result: Succeeded`；`FPSGAMEEditor` 已由并行构建生成 `UnrealEditor-FPSGAME.dll`（10:23:00，Editor 对象 10:19–10:20 覆盖本次全部改动），符文刃补丁后的 Editor 重链已排入空闲批次（日志 `damage-numbers-mpfix3-20261018-editor.log`）。构建/重链期间未主动关闭编辑器。
- 并行阻塞修复：`FPSUDSBridgeComponent.cpp` 的局部变量 `Object` 重名（C4456）改为 `Component`；`FPSUDSHillsAtmosphere.cpp` 改用 UE5.8 的 `DirectionalInscatteringLuminance`；均为解除编译阻塞的最小改动，不改变功能语义。
- 用户测试：训练靶单发／连发／霰弹／靶心暴击；普通怪单发／暴击／击杀／多目标；主机客机各只看到自己的数字。
- 默认不启动游戏、PIE、截图或自动验收。
