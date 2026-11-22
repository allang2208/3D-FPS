# 双手剑格挡 V24 发布记录（2026-11-22）

用户 2026-11-22 认可「合格，作为正式的双手剑格挡动作替换旧的」。基线 `8415eb7fa`，提交 `95b2de5e6`（正文）、`1ffef17b5`（发布记录与索引）、`5a72f2f1b`（共用技能快照与补丁换行规则），均已推送 `origin/main`。

## 内容

- 正式资产（不在 Git 中，已装入本机 `Content`）：`/Game/Weapons/AzureRunesword20260913/A_RuneSword_Guard`、`_GuardHit`、`_GuardBreak`，长柄同名于 `/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations`，以及重烘后的 `DA_Sword_LongGrip`。改前 V23 原包与安装回执：`F:/FPSGAMEData/ArtProduction/RuneSword20260913/GuardKuboldV24/Install-20261122/`。
- 作者源与参考读数：`SourceAssets/RuneSword20260913/GuardKuboldV24/`。
- 文档：[格挡 V24 说明](../../Weapons/runesword-guard-v24-20261122.md)。
- 技能：个人维护入口 [双手近战与转刀](../../../skills/ue5-fps-arms-animation/references/two-handed-melee.md)「格挡 V24」段；随仓库的共用快照 `skills/_shared/ue5-fps-arms-animation/` 同步指向 V24（同日 `5a72f2f1b`）。
- 发布目录补丁换行规则已登记在 `.gitattributes`（`Docs/Publication/GuardKuboldV24/Integration/*.patch` 保持 LF）。
- 消费者路径已在提交中：`Content/ColdSteelData/items.json` 的符文剑 `animation_folder` 指向 `/Game/Weapons/AzureRunesword20260913`，长柄目录 `Grips20260919/LongGripAnimations` 见各双手剑模块表；运行时按 `RuneSwordPresentation.cpp` 的 `Folder + "/A_RuneSword_" + Clip` 加载 `Guard`/`GuardHit`/`GuardBreak`。本次不改配置键。
- 迭代归档：[清单](F:/FPSGAMEData/ArtProduction/RuneSword20260913/GuardKuboldV24/Cleanup-20261122/archive-manifest.json)，文件在 `trash/runesword-guard-v24-20261122/`（Git 忽略）；推送工具的一次性文件归档在同批 `publish-archive-manifest.json`。

## 运行时以补丁发布

`Source/FPSGAME/Weapons/RuneSwordGuard.cpp`、`RuneSwordGuardTuning.h` 是并行会话共用的宿主，工作区版本还含其他会话未发布的格挡/工具格挡改动，因此只发布本任务的最小 HEAD 相对补丁：

| 文件 | 补丁 | 前 | 后 |
| --- | --- | --- | --- |
| `RuneSwordGuard.cpp` | [Integration](Integration/Source__FPSGAME__Weapons__RuneSwordGuard.cpp.patch) | `f8de368e…` | `dc453631…` |
| `RuneSwordGuardTuning.h` | [Integration](Integration/Source__FPSGAME__Weapons__RuneSwordGuardTuning.h.patch) | `91921f33…` | `a8a259c1…` |

完整散列见 [integration-prerequisites.json](integration-prerequisites.json)。两份补丁已在 `git archive 8415eb7fa` 的干净树上 `git apply --check` 通过，应用结果与作者内容逐字节一致，且不含其他会话的符号（`ToolGuardInstance`、`GuardItem`、`EagleTalon` 等）。

## 验证与未测

- 编译：2026-11-22 21:33 FPSGAMEEditor 构建成功（`Saved/BuildEditor/build-20261122-213346.log`），`UnrealEditor-FPSGAME.dll` 21:34 生成。
- 未自动测试；用户已确认动作观感。
