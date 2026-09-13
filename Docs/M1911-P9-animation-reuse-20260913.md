# M1911 与旧 P9 动作复用评估

> 历史开发阶段记录；当前路径、手枪标准及本次审计见 [M1911 开发审计](Weapons/m1911-development-audit-20260913.md)。已否决的首版动画导出与一次性 integrate_runtime.py 移入本机 trash，重建依赖的 Blend 和作者脚本仍保留。

用户反馈当前 M1911 手部扭曲、ADS 遮挡；本次仅按要求读取动作源、作者脚本、骨架、既有动作表与预览，未替换游戏资产，未启动游戏或执行运行回归。

## 结论

建议使用旧 Godot P9 的原始 Infima 手枪动作作为迁移母版，保留当前 Manny 手臂/手套和 M1911 枪型。可复用的是整臂动作、双手分工、换弹时序及配套机械动画；Godot 成品不能不经适配直接替换 UE 动画。

当前 M1911 的 `build.py` 从 M4 待机与第 95 帧弹匣手型构造握持，再以自写双段手臂求解、手腕平移和旋转制作手枪动作，没有采用 P9 的现成整臂轨迹。该首版已被用户否定，不应作为成熟手枪动作基准。

## 已定位的本地源

- 原始手臂 FBX：`E:/3d/infima-fps-staging/reference-art/Art/Animations/Character/Handguns/`
- 原始枪械及机械动画：`E:/3d/infima-fps-staging/reference-art/Art/Meshes/Weapons/Handguns/SK_Handgun_03.fbx`
- Godot 转换 GLB：`E:/3d/infima-fps-staging/converted/infima_handgun.glb`
- 旧可编辑源：`E:/无尽轮回/3d/free-hands-20260908/editable-v6/infima_handgun.blend`
- 旧动作表：`E:/无尽轮回/3d/free-hands-20260908/animation-v6-review/infima_handgun-false-standard-reload_empty.jpg` 与同目录 `equip_charge`、`reload` 等图。
- 旧运行逻辑副本：`E:/无尽轮回/3d/free-hands-20260908/infima_viewmodel-before-hands-install.gd`。

读取原始 FBX 得到 30 fps 动作范围，时长按首末关键帧间隔计算：

| 动作 | 原始帧范围 | 时长 |
|---|---|---|
| Idle Pose | 1–2 | 静态姿态，0.033 秒 |
| Aim Pose / Fire / Aim Fire | 1–23 | 0.733 秒 |
| Reload | 1–68 | 2.233 秒 |
| Reload Empty | 1–83 | 2.733 秒 |
| Unholster | 1–29 | 0.933 秒 |
| Holster | 1–24 | 0.767 秒 |
| Inspect | 1–150 | 4.967 秒 |

枪械 FBX 中还包含与手臂时长相配的普通/空仓换弹、射击、Slide Back Pose。不能只迁移手臂而遗失弹匣与套筒轨道。旧 Godot `equip_charge` 是从空仓换弹 1.75 秒之后的片段生成，加入 0.18 秒起始过渡，不是单独的原始装备拉套筒 FBX；移植时需要重做与 M1911 的接触映射。

## 骨架和现有画面的限制

P9 原始手臂为 68 骨骼；实际 M1911 导出骨架 `SK_M4_Infima` 为 108 骨骼。68 个源骨名在目标中均存在，但 13 个共同骨骼的父级不同，包括锁骨、掌骨/第一指节、根、头颈。原始单位及参考姿态也不同。应按完整层级与参考姿态迁移动作，处理目标掌骨、twist 与权重；不可直接复制同名骨骼局部旋转。

作者文件另保留 263 骨骼的 `Armature` 控制源，它不是本次实际导出的骨架。读取导出 FBX 仅得到 `SK_M4_Infima`、`SK_Manny_Arms_Export`、`M1911_Export`，未发现作者控制形状混入此 FBX。

本次实际查看的旧 P9 换弹动作表中仍可见手指交叠；不能把旧换手模后的成品当作无瑕疵交付。采用原始整臂动作，再在 Manny 手上适配 M1911 握把、弹匣和套筒，避免照搬旧手型问题。

ADS 遮挡物尚未在当前游戏画面中识别。当前代码按准星与照门轴线求 ADS 位姿，但该计算不能保证手臂和枪体不遮挡镜头；更换动作后仍需针对新姿态调整。未宣称已定位遮挡物或已修复。

## 来源与许可

本地 `handgun-provenance.json` 指向第三方 GitHub 仓库 `SakanakoChan/FPSGameBySakanako` 中的 Infima Low Poly Shooter Pack - Free Sample。公开仓库提供来源线索，不等于原作者另行开放全部资产授权。

[原始免费包页面](https://assetstore.unity.com/packages/templates/systems/low-poly-shooter-pack-free-sample-144839) 当前列明 Standard Unity Asset Store EULA。另一套 [Fab Free FPS Template](https://www.fab.com/listings/6a0af880-2b74-480c-a82c-8e597918dffe) 的 CC BY 记录不能套用到旧 P9 包。正式复用应保留对应原包的取得记录与许可，原始二进制不随项目公开上传。

原始读取结果：`Saved/M1911P9Review20260913/source_inventory.json`；读取脚本同目录 `inspect_sources.py`，未保存或修改原始 Blend/FBX。
