# 炼药台金色细线：枪械镭射未隐藏（独立修复）

日期：2026-10-18  
范围：炼药台进入工作视角后，瓶身/勺子/桌面上的金色细线。

> **2026-10-18 00:34 更正：本条不是最终线源。** 最终确认线源是 [RedRoot 瓶盖长提取管](alchemy-cap-pipette-line-fix-20261018.md)。镭射隐藏仍然是一个真实的工作视角隐患，修复保留；但它不能解释“从瓶口出发”的那条线。

## 原结论（部分成立，但非本次线源）

枪械的金色镭射（Blessed Laser）也会作为独立世界组件残留；这部分修复保留。

![实机：倒配料时横穿场景的金色镭射](../../SourceAssets/PotionWorkbenchDesign20261015/SeamFix20261017/UserReport/user_gold_laser.png)

## 根因

`AAlchemyWorldView` 进入工作视角时，把玩家 pawn 加进：

```cpp
Player->HiddenActors.Add(WorkingPawn.Get());
```

`PlayerController::HiddenActors` 只影响该相机的可见性，**不会把 `AActor::IsHidden()` 变成 true**。

`UTacticalDeviceComponent` 的镭射由三个**独立世界组件**组成：

- `Beam`：从枪口到命中点的长条网格；
- `Dot`：命中点光斑；
- `Light`：激光点光源。

它们没有挂在枪械网格下，因此枪/手臂被相机隐藏后仍然渲染。`TickComponent` 原来只检查 `C->IsHidden()` 和 `Host/Body` 的可见性，抓不到 `HiddenActors`，金色 Beam 就继续横穿炼药台。倒配料、搅拌、舀取时都会被这条线穿过，看起来像每个物体上都有细线。

## 修改

`Source/FPSGAME/Weapons/TacticalDeviceComponent.cpp` 的 `TickComponent` 在原有可见性判断前增加：

```cpp
if(const auto* PC=C?C->GetController<APlayerController>():nullptr;
   PC&&PC->HiddenActors.Contains(C))
{HideEffects();return;}
```

`HideEffects()` 会隐藏 `Beam/Dot/Light` 并清掉激光采样；离开工作视角、`HiddenActors` 移除后自动恢复。

这同时覆盖了同样用 `HiddenActors` 隐藏 pawn 的木工台、锻造台、枪械组装台，避免其他工作视角残留镭射。

之前针对 hover 描边的 `SetHoverTarget` 改动**已回滚**，UI 仍保留“金边器具可操作”和原 hover 行为；模型底环/铜箍/硬边清理保留，但都不是这条金线的修复。

## 构建

- Game：`Saved/BuildGame/build-20261018-000308.log`，`Result: Succeeded`
- Editor：`Saved/BuildEditor/build-20261018-000535.log`，`Result: Succeeded`

构建过程中另一个新增文件的 UHT 参数遮蔽（`FPSPracticeTarget.h` 的 `MulticastPracticeHit(..., Instigator)`）阻断了编译，只把该参数改名为 `InInstigator` 解阻，行为未变。

## 边界

- 没有打开可见编辑器，没有 PIE/游戏内视觉验收。
- 需要重开编辑器/PIE 让新 DLL 生效；打包版本需要重新 cook/构建。
- 如果还有线，先看是不是**枪械镭射之外的另一个世界组件**：光束/点光/手电/曳光弹也可能由独立组件渲染。

