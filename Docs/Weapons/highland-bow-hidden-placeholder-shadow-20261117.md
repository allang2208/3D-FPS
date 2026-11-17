# 高地长弓持握时的块状阴影修复（2026-11-17）

用户截图显示持弓时人物附近出现宽大的实体块状阴影。本轮按该问题排查源码并修复，不打开 UE，不执行游戏、渲染或额外验收测试。

## 已定位的代码问题

`UFPSPlayerBodyComponent::BuildBow` 为弓弦保留 Upper / Lower 两个备用圆柱；`UBowPartComponent::AddRod` 创建的占位模型是 `/Engine/BasicShapes/Cylinder`，默认高 100 cm、半径 50 cm。

高地长弓的山鸣、疾律使用独立骨骼弓弦。`PoseString` 成功后会隐藏备用圆柱，也不会调用 `StretchRod` 把圆柱缩成细弦。原 `UpdateBowVisibility` 只按槽位是否启用决定投影，同时开启普通阴影与隐藏阴影，忽略具体网格的 `IsVisible()`。因此被隐藏的默认大圆柱仍进入阴影；这是与截图相符的确定代码缺陷。通过现有编辑器对用户当前 PIE 角色作只读读取，`Upper_0`、`Lower_0` 均为引擎 Cylinder、世界缩放 1、`visible=false`，但 `cast_shadow=true`、`cast_hidden_shadow=true`、`owner_no_see=true`。第一人称弦的备用圆柱投影标志为 false，异常来自世界弓具。读取结果保存在 `Saved/HighlandBowShadow20261117/diagnosis-live.json`；没有启动、停止或操控试玩，没有重拍画面。

此外，原代码对弓体槽递归遍历所有下属槽，先用弓体的可见性给箭、弦等子槽设置阴影，再在各自循环覆盖。

## 修改

仅修改 `Source/FPSGAME/Characters/FPSPlayerBodyBow.cpp` 的 `UpdateBowVisibility`：

- 每个槽只处理直接挂接的渲染组件，避免父弓体覆盖其他槽的显示策略。
- 阴影条件同时要求槽位有效、未收起和该网格 `IsVisible()`；备用圆柱、未显示的箭或备用网格不再因为隐藏阴影重新投射。
- `OwnerNoSee` 与网格自身可见性继续分开：第一人称下正常世界弓具仍投影，第三人称和队友可见的弓体也保留投影。

保留全部弓模型、配件、观峰瞄具、手部动作、骨骼弓弦变形与备用细弦回退、伤害和玩法数值。不修改 UE 资产或玩家存档。

## 构建与交付

Game / Editor 常规构建均成功并落盘，结果记录在 `Saved/HighlandBowShadow20261117/delivery.json`。此前对现有 PIE 仅作定向只读诊断；构建进入 Editor 阶段时原编辑器已退出、DLL 占用已释放，本轮未发送热编译、退出或重启命令。未启动 UE、游戏或渲染，未进行修复后实机验收，效果由用户自行测试。
