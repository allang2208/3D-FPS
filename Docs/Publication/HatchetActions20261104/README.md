# 碳钢战斧专属动作：发布清单（2026-11-04）

任务：`ue_tactical_hatchet` 的专属动作——装备抛接 V2、三连击第三段单持劈砍、双斧劈砍、双持冲刺就绪跑姿（Enter/Ready/Exit），以及双持旋风副手的自然垂放与第一人称转身修正。说明正文见 [tactical-hatchet-20261101.md](../../Weapons/tactical-hatchet-20261101.md)。

## 这个任务发布什么

**直接提交（武器自有宿主）**

| 文件 | 说明 |
| --- | --- |
| `Source/FPSGAME/Weapons/Kukri/HatchetDrawRhythm.h` | 装备抛接的镜头/音效表（生成） |
| `Source/FPSGAME/Weapons/Kukri/HatchetChopRhythm.h` | 单持劈砍的 FSwing/FStrike/FRift + 镜头 + 剑气（生成） |
| `Source/FPSGAME/Weapons/Kukri/HatchetDualChopRhythm.h` | 双斧劈砍，时间轴钉住 `DualThrust*`（生成） |
| `Source/FPSGAME/Weapons/Kukri/HatchetReadyRhythm.h` | 就绪跑姿三段 clip 路径与时长（生成） |
| `Source/FPSGAME/Weapons/Kukri/KukriLeftRest.h` | 左臂自然垂放姿势表（生成） |
| `Source/FPSGAME/Weapons/Kukri/KukriDashAttack.cpp` | 从就绪跑姿进入冲刺攻击的混合时间（见下方依赖） |
| `Source/FPSGAME/Weapons/Kukri/KukriWhirlwind.cpp` | 双持第一人称转身 + 左手垂下（见下方依赖） |
| `SourceAssets/HatchetEquip20261101/` | 作者脚本、参考读图脚本、README、`clips.json` |
| `SourceAssets/HatchetChop20261102/` | 同上（单持 + 双斧劈砍） |
| `SourceAssets/HatchetSprint20261103/` | 同上（就绪跑姿三段） |
| `SourceAssets/Kukri20261020/author_kukri_left_rest.py` | 生成 `KukriLeftRest.h` |
| `Docs/Weapons/tactical-hatchet-20261101.md` | 全部动作的记录 |

`SourceAssets` 只发布 `.py` / `.json` / `.md`；密集 clip（`Clips/`）、预览（`Previews*/`）、探针（`Work*/`）和参考抽帧按 `.gitignore` 留在本机。

**Integration 补丁（共享宿主，`Integration/`）**

`KukriWeaponComponent.{h,cpp}`、`KukriStrike.cpp`、`KukriRift.cpp`、`KukriArmsMeshComponent.{h,cpp}`。这些文件在工作区里还叠着其他会话未发布的层（模块外观 `MainModules`、命中回执 `KukriDecisiveComponent`、`bMirrorRightToLeft` 镜像层等），整文件提交会连带发布他人工作，所以只以 HEAD 相对补丁发布本任务的 hunk。

补丁全部在干净 HEAD（`19d733c3`）上用 `patch -p1` 验证过，**6/6 零 fuzz**。校验值见 `integration-prerequisites.json`。

## 不能从 HEAD 相对补丁发布的两处

`KukriWhirlwind.cpp` 与 `KukriDashAttack.cpp` 在 HEAD 上是**旧版本**：HEAD 的旋风还没有 staff-offhand 层、`ClipTime`/`Pair` 重构和 `bDualHatchet`，冲刺攻击也还没有网络回执层。本任务在这两个文件上的改动（第一人称转身修正、左臂垂下、就绪跑姿入口混合）是**叠在那些未发布层之上**的，无法表达成 HEAD 相对补丁。

处理方式：随本任务提交**工作区整文件**，并在 `integration-prerequisites.json` 的 `requires` 里写明依赖。等那一层发布后，这两个文件会自然带上这些改动；在那之前不要把它们当作可单独应用的补丁。

## 如何应用

```bash
# 在干净 HEAD 检出上
for p in Docs/Publication/HatchetActions20261104/Integration/*.patch; do patch -p1 -i "$p"; done
```

补丁只加本任务的 hunk。应用后仍需本任务提交里的 `Hatchet*Rhythm.h` / `KukriLeftRest.h`（武器自有宿主，已在同一次提交中）才能编过。

## 验证边界

- `FPSGAMEEditor Win64 Development` 构建 Succeeded（本机多会话共享工作区，构建日志见 `Saved/BuildEditor/`）。
- Game 目标未构建。
- **未运行游戏、未测试、未验收**；动作观感与联机表现由用户测试。
- 第三人称的劈砍/旋风沿用既有全身动作，本轮没有单独制作。
