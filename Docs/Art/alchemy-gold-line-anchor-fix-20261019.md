# 炼药台金色细线：根因确认与修复（2026-10-19）

## 结论

**根因：工作视角手臂的躯干锚点被固定在镜头后方，手要够到 1 米外的台面，臂展只有约 50 cm，于是 `Solve()` 的够手距离 `Clamp` 每帧都触发，肩膀被强行搬到台面上，肩部蒙皮被拉成一条贯穿屏幕的细带。**

运行期已确认：工作视角执行 `showflag.SkeletalMeshes 0` 后线消失 → 线属于骨架蒙皮，不是静态网格、不是后处理、不是镭射。

## 定位过程（本次新增的确证）

用户提供的关键描述把范围一步步收紧：

1. **待机没有，只有操作时才有**（倒料/搅拌/装瓶三种都有，研磨与沙漏没有）→ 排除所有静态实物：锅、桌面、瓶盖、接缝、hover 描边在待机时也都在画面里。
2. **线跟着手上的瓶子/工具走**，且**从工具上伸出去、比杆长很多、几乎贯穿屏幕** → 一端随手移动、另一端固定在别处，这是蒙皮拉伸的特征，不是实体构件。
3. **`showflag.SkeletalMeshes 0` 后消失** → 锁定骨架蒙皮，不是后处理、不是世界组件。

工作视角里只有两种骨架网格：手臂 `SK_M4_BareArmsV7` 和手册书页 `UBookLeafComponent`。书页用固定页宽积分、缩放沿用 `Ref.GetScale3D()`，不会拉长，且位置在画面左侧，不符合"跟着工具走"。因此锁定手臂。

## 根因（代码）

`Source/FPSGAME/Building/AlchemyWorldView.cpp` 的 `Tick`：

```cpp
// 修复前：躯干固定在镜头后方
const FTransform Torso(BodyRotation,Eye+FVector(0,-13,-35));
```

`Solve()` 里：

```cpp
FVector Shoulder=Pose[H.Upper].GetLocation();               // 躯干位置
const float D=Clamp(Distance(Wrist,Shoulder), ..., L1+L2-.2);
Shoulder=Wrist-Axis*D;                                      // 肩膀被重新推导
```

实测各操作的手腕目标到躯干的距离，对比约 50 cm 的臂展上限：

| 操作 | 手腕到躯干 | 是否超限 |
|---|---|---|
| 搅拌 | 122.0 cm | 超限 |
| 舀勺浸入 | 115.8 cm | 超限 |
| 倒料瓶口 | 115.7 cm | 超限 |
| 量瓶 | 82.2 cm | 超限 |

**全部超限**，`D` 每帧被 clamp 到 49.8 cm。肩膀因此被放到"手腕后方 49.8 cm"处，等于被搬到台面附近，实测位移：

| 操作 | 肩膀位移 |
|---|---|
| 搅拌 | 72.2 cm |
| 舀勺 | 66.0 cm |
| 倒料 | 65.9 cm |
| 量瓶 | 32.4 cm |

肩部/三角肌蒙皮的一端在 `clavicle`/`upperarm`（跟着手到台面），另一端在躯干绑定位置，被拉开 66–72 cm，形成细长条带——投影出来就是那条几乎贯穿屏幕的 1 px 线。

**为什么前三轮修复都无效**：

- 折叠修复（`AlchemyWorldView.cpp` L104–115）只处理 `!ArmBones.Contains(I)` 的骨骼，而肩部蒙皮恰恰**在手臂骨上**（`clavicle` 及其全部子骨都在 `ArmBones` 里），不在折叠范围。
- 瓶盖提取管、镭射、hover 描边是另外三个独立问题，都不是这条线。
- 手臂网格本身是干净的：`Work/mesh.npz` 扫描显示最长边 p100 = 1.71 cm、零退化面，所以不是建模问题，是**形变**问题。

## 修复

`AlchemyWorldView.cpp` 的 `Tick`：把躯干锚点从"固定在镜头后方"改为"沿原位置向工作手滑动，取第一个使工作手进入安全带的位置"。

```cpp
const FVector Base=Eye+FVector(0,-13,-35);          // 原始锚点
const float Limit=FMath::Max(1.f,ArmSpan)-.2f;      // Solve() 的 clamp 上限
const float SafeLimit=Limit*AlchemyReachSafety;     // 0.9 倍，留余量
// 只有真正握工具的手参与：Stir/Timer 的左手停在闲置位
const bool LeftWorks=Bottle||ToolMode==EAlchemyOp::Pour||Grind;
Anchor=Base;
for(int32 Step=0;Step<=64;++Step)
{
    const float T=Step/64.f;
    const FVector Candidate=FMath::Lerp(Base,Center,T);
    Anchor=Candidate;
    if(WorstReach(Candidate)<=SafeLimit)break;
}
```

要点：

- **操作时**：锚点从 `Eye+(0,-13,-35)` 线性滑向工作手中点，取**第一个**满足条件的位置，最大限度保留原始构图。
- **只约束工作手**：`Stir`/`Timer` 的左手停在 `(195,-133,113)`（不是工具），让它参与会让约束互相矛盾、无解。
- **安全系数 0.9**：工作手落在 clamp 上限的 90% 以内，`Solve()` 的 `Clamp` 永远不会触发。
- **待机时**：锚点不变，静止手位与修复前完全一致。
- 折叠逻辑保留（无害防御），但不再是本 bug 的修复。

### 数值验证（按最终代码逐行复算）

| 操作 | 滑动比例 t | 锚点 | 距锅心 | 工作手最远 | clamp |
|---|---|---|---|---|---|
| 倒料 | 0.62 | (196.4,-138.6,138.5) | 43.4 | 43.4 cm | 否 |
| 研磨 | 0.78 | (68.3,-86.3,114.7) | 157.9 | 43.0 cm | 否 |
| 搅拌 | 0.64 | (207.6,-139.1,142.4) | 37.4 | 43.8 cm | 否 |
| 装瓶 | 0.75 | (196.8,-139.5,132.0) | 43.8 | 43.8 cm | 否 |
| 计时 | 0.73 | (162.1,-85.6,114.3) | 66.1 | 42.8 cm | 否 |

五种操作全部脱离锅体、`Clamp` 均不触发，工作手最远 42.8–43.8 cm（上限 49.8 cm）。待机沿用原锚点，仍会 clamp，与修复前一致。

## 第一次修复的 bug（已修正）

初版把方向算反了：

```cpp
// 错误版本
const FVector TowardEye=(ReachCenter-Eye).GetSafeNormal();   // 这是"背离镜头"
const FVector Anchor=ReachCenter+Back*20.f;                  // 结果推向场景深处
```

`(ReachCenter-Eye)` 是**从镜头指向手**的方向。再叠加 `+Back*20` 等于把手部锚点往场景深处推 20 cm，实测四种操作的锚点**全部落进坩埚内部**（水平距锅心 1.9–27.8 cm），肩膀和上臂整段埋在锅体里，于是第一人称手臂看不见。

线确实消失了（clamp 真的不再触发），但代价是躯干被塞进锅里——属于把问题换成了另一个问题，用户实测发现后已更正。

## 代价与已知影响

锚点靠近手之后，**肩膀和上臂会进入画面**。按 `AlchemyTabletop.h` 的脚本相机投影对比（相对变化可信，绝对坐标因实测相机与脚本不一致仅供参考）：

| | 右肩 | 左肩 |
|---|---|---|
| 旧锚点 | x=1067，深度 58 cm（贴边/出画） | y=853，深度 39 cm（出画） |
| 新锚点 | x=980，深度 104 cm（入画） | x=980，深度 104 cm（入画） |

也就是说手臂的入镜角度和长度会与之前不同，这是方案 A 的固有代价，需用户试玩确认可接受。

如果入镜观感不合适，可调整后撤距离（20 cm → 更大）：后撤 40 cm 时最远够手 48.9 cm，仍在 49.8 cm 内但余量仅 1 cm；后撤 50 cm 就会重新触发 clamp（58.7 cm），不能超过。

## 验证状态

- 静态数值验证：完成（见上表）。
- 编译：**完成**。
  - Editor：`Saved/BuildEditor/build-20261019-124347.log`，`[1/4] Compile AlchemyWorldView.cpp` → `[3/4] Link UnrealEditor-FPSGAME.dll`，`Result: Succeeded`。`UnrealEditor-FPSGAME.dll` 12:44:08。
  - Game：`Saved/BuildGame/build-20261019-124816.log`，`[1/3] Compile AlchemyWorldView.cpp` → `[2/3] Link FPSGAME.exe`，`Result: Succeeded`。`FPSGAME.exe` 12:48:41。
  - 均为源码 12:40:26 之后的重编+重链，非缓存复用。
- 游戏内视觉验收：**未做**，按用户规则由用户自行测试。

## 复现与回退

- 修改文件：`Source/FPSGAME/Building/AlchemyWorldView.cpp`（仅 `Tick` 内的锚点计算，约 +64 行）。
- 回退：删除 `Base`/`ArmSpan`/`Limit`/`SafeLimit`/`LeftWorks` 与滑动循环，把 `Anchor` 改回 `Eye+FVector(0,-13,-35)` 即可恢复原行为。
- 相关历史文档（均已被本轮推翻或降级）：[近裁剪面蒙皮细条](alchemy-arms-near-plane-sliver-fix-20261018.md)、[RedRoot 瓶盖长提取管](alchemy-cap-pipette-line-fix-20261018.md)、[枪械镭射未隐藏](alchemy-laser-hide-fix-20261018.md)、[第三轮复排](alchemy-gold-line-third-audit-20261019.md)。

## 编译（最终版）

| 目标 | 日志 | obj | 产物 |
|---|---|---|---|
| Editor | `Saved/BuildEditor/build-20261019-141732.log` | 13:47:03 | `UnrealEditor-FPSGAME.dll` 14:10:57 |
| Game | `Saved/BuildGame/build-20261019-1418*.log` | 14:00:37 | `FPSGAME.exe` 14:14:44 |

两个目标的 obj 与产物均晚于源码 13:43:06，`Result: Succeeded`。

## 联机复核（2026-10-19 事后审计）

**结论：改动对网络层无影响，但有两点需要在联机验收时留意。**

### 为什么没有联机风险

1. `AAlchemyWorldView` 构造函数里 `SetReplicates(false)`，且只由本地 UI 的 `PrepareView()` 生成（`ColdSteelAlchemyWidget.cpp` L129-133，有 `if(View||...)return;` 防重入）。**专用服务器上根本不存在这个 Actor**。
2. 改动只读 `Right`/`Left` 两个本地计算出来的手腕目标，不读写任何 `UPROPERTY(Replicated)`，不调用 `RPC`，不参与 `HasAuthority()` 分支。
3. `PotionWorkbenchVisualComponent::Configure` 在 `NM_DedicatedServer` 下直接 `return`，服务端连视觉组件都不构造。
4. 代码中唯一的复制状态间接依赖是 `Visual->HandTool()`（读复制的 `State.Tool`），且只用于选择本地表现分支，不参与任何状态同步或权威判断。

### 需要在联机验收时留意的两点

1. **锚点跳变（视觉，非功能）**：`Acting` 由复制状态 `State.Tool`（经 `HandTool()`）推导。操作结束、`Tool` 从 `Stir`/`Pour`/`Bottle` 回到 `Stop` 时，`Acting` 翻假，躯干锚点从手部锚点跳回 `Eye+(0,-13,-35)`，实测位移 **100–208 cm**。
   - 但 `Solve()` 每帧从手腕反推肩膀，**手腕不会动**，跳变的只是肩/上臂，且发生在玩家松手离开工具的那一刻。
   - 联机延迟下 `State.Tool` 到达更晚，跳变时刻会比本地稍延后，属观感问题。
2. **复制延迟下的首帧**：刚进工作台时 `State.Operator` 可能尚未同步，`Acting` 为假走待机分支；状态到达后再切到操作分支。这同样是上面的跳变，只发生一次。

### 待机分支仍在 clamp（已知、非本次回归）

待机锚点未改，`R idle` 60.7 cm、`L idle` 84.3 cm 仍超 49.8 cm 上限，肩部蒙皮在静止姿态下依然被拉伸。这一点**在本修复之前就存在**（待机一直用镜头锚点），且用户实测待机看不到线。

原因推测：待机时两手离镜头近（60–84 cm），拉伸段短且被手臂本体遮挡，投影不成细线。两条分支与视线夹角实测为待机 27–29°、操作 38–46°，差异不足以单独解释，**该推测未经验证**，如需彻底消除可后续把待机分支也改为手部锚点（会改动静止手位，需另行确认）。

## 2026-10-19 收尾清理（本轮）

按用户决定"只保留修复、不追手部入镜"，已删除本轮所有非修复内容：

- **删除折叠代码块**（`if(ArmBones.Num() && Hands[0].Clavicle>=0 …)` 那段）。它来自 10-18 轮，在 V9 上**影响 0 个顶点**（蒙皮权重只落在 24 根手臂骨，无任何非手臂骨），属空操作。已确认 HEAD 版本不含它，是本轮之前的遗留。
- **删除临时诊断代码**（`ALCHEMYARMS` 日志 + `AlchemyArmsDiag.txt` 写文件）。该段曾用错 `FFileHelper::SaveStringToFile` 重载签名，**导致打开炼药台面板闪退**，已彻底移除。
- **删除多余 include**（`#include "AlchemyManualComponent.h"`），仅为诊断访问 `Manual` 而加。
- 最终 diff 为 **49 增 5 删**，只含锚点滑动修复。
- 临时文件（备份与中间数据、分析脚本与截图）已归档到仓库外 仓库外临时目录。

### 本轮的错误判断（记录以免重犯）

1. **误以为"手看不见"等于"修复失败"**，据此回退了有效的锚点修复，导致细线复现。两者是独立问题：锚点修复只解决细线。
2. **误判"空间错配"**：曾用日志里 `armsLoc`（世界坐标）与 `handL`（Actor 空间）直接相减得出 8 米差距。实际上 `AAlchemyWorldView` 每帧 `SetActorTransform(Station->Body()->GetComponentTransform())`，台面局部坐标即 Actor 空间，两者本自洽，不存在错配。该结论已撤回，未写入任何代码或文档。
3. **误用 `-Rebuild`**：为恢复一个丢失的 obj 而全量重编，撞上其他任务未提交的破损代码（`SniperSuppressorAssets.h` 缺失等），产生大量无关报错。正确做法是增量编译。

### 仍未解决

**第一人称手臂在炼药台工作视角中不可见**，物品呈"漂浮移动"。这与细线是独立问题，本轮按用户要求不再处理。
