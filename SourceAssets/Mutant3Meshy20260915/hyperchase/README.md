# 突变体-3 / Hyper Chase 接续

日期：2026-09-15。后续用户改为指定旧 Godot 奔跑僵尸，已通过 [../godot_runner/README.md](../godot_runner/README.md) 接入。Hyper Chase 保留为未采用的商业候选，未取得其源文件；以下为当时的准备记录，不再是当前工作的阻塞条件。

## 源文件

- 候选为 MoCap Online `Zombie_HyperChase_1_Loop` 至 `Zombie_HyperChase_5_Loop`，实际选用片段须先查看动作。不能仅根据编号推断哪个最合适。
- [官方产品与动作清单](https://mocaponline.com/products/zombie)：Starter 含 HyperChase 1；Basic 含 1–4；Pro 含 1–5。优先取得 UE4 格式及其源 FBX，保留源参考骨架。购买版本由用户决定，未代购。
- [官方在线预览](https://mocaponline.com/pages/animviewer/zombie-pro)。此前浏览器播放器读取失败，尚未实际完成五种狂奔的视觉比较。
- 已下载 [官方免费样例](https://mocaponline.itch.io/mocap-online-demo) 到 `sources/MCO_Demo_Pack_v2.zip`。文件为 243,871,365 字节，僵尸 FBX 仅含 `Zombie_Chase_1_Loop` 及其 `_IPC` 版本，没有 Hyper Chase；不把此样例当作已经取得的狂奔动作。
- 已查找项目 Content/SourceAssets、`D:/FPS3D/资产`、用户 Downloads 和 Epic VaultCache，没有找到 Hyper Chase / MoCap Zombie 包。用户若已有其他存储位置，可直接从该位置接续。
- [许可入口](https://mocaponline.com/pages/licensing)。官方商业动画不是 Mesh2Motion CC0，不公开提交原始资产，不把来源许可并入旧 CC0 记录。适配使用 UE 原生 IK 与常规骨骼编辑。

## 接入范围

1. 保留已安装 revision2 的 Hit_Chest，保留原 Meshy 网格、34 根原骨、蒙皮、材质、Walking、Idle、Attack、Death、Rage 与物理资产。
2. 取得正版源后，读取源奔跑周期、原地/根运动版本与速度；选择重心前压、步幅有力量、手臂有攻击意图的狂奔，避免再从 Jog 改造。源动作选择先于烘焙。
3. 在既有 `UEAuthoring/Mutant3Authoring.uproject` 中建立该源骨架到 Mutant3 的独立 IK Rig / IK Retargeter；现有 `RTG_M2M_Mutant3` 只适用于 M2M 源，不能直接套用 MoCap 源骨架。
4. 独立保留原动作、原生重定向输出与体型修正结果；新源动作先导出为候选 FBX，再接到 `/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Running` 和 `A_Mutant3_RunFast`。
5. 保留 CharacterMovement 的世界移动与 360 cm/s 最大追击速度；动画采用原地循环，播放节奏按实际步幅适配，不把游戏速度修改为素材包示范速度。
6. 保留攻击命中 0.40–0.51 s、弹反立即打断击退并倒放 0.3 s、Stagger 0.9 s、死亡 60% 转布娃娃。完成实际安装后才更新主动画合同与 active_revision。

无需为当前资料准备编译 C++。之后接入的游戏效果按用户规则由用户测试。
