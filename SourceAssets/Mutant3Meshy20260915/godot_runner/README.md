# 突变体-3：旧 Godot 奔跑僵尸动作移植

2026-09-15：已完成源动作读取、UE 原生 IK 重定向、Meshy 原蒙皮上的动画烘焙及两条正式动画导入。没有启动游戏或对新成品追加截图、渲染、回归测试；游戏效果由用户测试。

## 找到的实际来源

旧工程位于 `E:/3d/trash/repository-ue5-root-20260910`。`scenes/enemies/runner_zombie.tscn` 使用 `runner_zombie_v02.glb`，继承链为 humanoid_variant_zombie → modern_zombie → ordinary_zombie。移动时播放 `Walk`，该别名来自 **Denys Almaral 的 running_58f**，不是旧备用 zombie_anim.gd 使用的 Quaternius Run_Arms。

源周期 58/30 = 1.9333 s，原地循环。Godot 按实际移动速度 / 2.357897 m/s 累进动画时间，场景追击速度为 2.8 m/s。此次读取了实际源模型的 8 个相位，源参考留在 `source_preview/`；动作前倾、双腿交替迈步，手臂保持屈肘和左右不对称摆动。这些图片是用户要求查看的旧动作，不是新目标模型的验收截图。

## 移植与当前引用

- 保留现有 Meshy 网格、34 根原骨、权重、PBR、Walking、Idle、Attack、Death、Rage、Hit_Chest 和 Physics Asset。
- 使用独立 `IK_GodotRunner` / `RTG_GodotRunner_Mutant3`，不复用不匹配的 M2M 源骨链。源骨名中的空格在 FBX 导出时改成下划线。
- 保留源上下身动作，仅处理两副骨架的参考姿态、体型、地面穿入和周期末尾 40 ms 衔接。没有叠加 Jog 或另一个僵尸上身。
- 原地动画由 CharacterMovement 移动。按源参考速度及目标/源腿长比 0.987144 调整时间，适配现有 Running 240 cm/s 和 RunFast 360 cm/s 的动画参考速度；最大游戏追击速度保持 360 cm/s。
- 正式路径 `/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Running` 为 1.875 s、225 个 120 FPS 区间；`A_Mutant3_RunFast` 为 1.25 s、150 个区间。
- 攻击命中 0.40–0.51 s、弹反立即打断击退和倒放 0.3 s、Stagger 0.9 s、死亡 60% 转布娃娃均沿用既有实现。未改 C++，无需编译原生模块。

## 重建与恢复

`prepare_source.py` → 在 `../UEAuthoring/Mutant3Authoring.uproject` 执行 `retarget_source.py` → Blender 执行 `author_runs.py` → 关闭占用正式资源的 FPSGAME 编辑器后，在 FPSGAME.uproject 执行 `install_runs.py`。

prepare_source.py 默认只导出源资产；显式添加 `-- --preview` 才生成旧动作参考帧。新可编辑完整源为 `Mutant3_Meshy_GodotRunner.blend`，两个引擎输入位于 `final/`。原始 Godot 文件、控制器快照与许可位于 `sources/`，原生输出位于 `native_retarget/`。制作工程保存源骨架与重定向器。

2026-09-19 归档时，将当前完整源按字节复制为同目录的 `Mutant3_Meshy_CombatBase.blend`，作为 `author_runs.py` 的固定输入。它保留网格、蒙皮、材质及当前非跑步动作；同目录放置保留原相对资源路径。重建现在不再读取 `../revision2/`。工作源仍为 `Mutant3_Meshy_GodotRunner.blend`；这两个 Blend 都是本机资产依赖，不在 Git 中。

Hit_Chest 的原生重定向输入、输出及最终 `A_Mutant3_Stagger.fbx` 单独保存在 [combat_base/](combat_base/README.md)。当前编辑源中的 BeforeGodotRunner / BeforeRevision2 动作仅为历史动作数据，不是正式导出选择。历史制作脚本及旧跑步包已移到仓库根 `trash/mutant3-animation-retired-20260919/`，逐文件恢复映射见 [归档清单](../../../Docs/AssetArchives/mutant3-animation-20260919.json)。旧 `previous_packages.json` 随旧包归档；今后再次执行安装器会在工作目录新建下一次替换前的备份。

只恢复跑步时使用本目录 `final/` 两条 FBX 与 `install_runs.py`；它不会覆盖 Stagger。完整恢复正式怪物还需要根目录保留的其他动作、模型/PBR 和 Physics Asset，不能只克隆 Git 视为资产恢复完成。

`installed.json` 是本次正式安装记录，`install.log` 是导入日志；导入命令完成不等于游戏画面通过。

## 署名与许可

Running animation derived from **ZombieMale_A / running_58f by Denys Almaral**, licensed under **CC BY 4.0**.

- Author release: https://denysalmaral.com/post/free-zombie-animations-for-your-games/
- Author showcase: https://denysalmaral.com/gamedev/free-zombies/
- License: https://creativecommons.org/licenses/by/4.0/
- Modifications: existing Godot gameplay alias and loop treatment; UE IK retargeting to the user-provided Meshy Forsaken Brute; body-size/grounding adjustment and time resampling into two locomotion speeds. No author endorsement implied.

发布游戏时保留上述作者、来源、许可与修改说明。该动作不属于 Mesh2Motion CC0；模型仍为用户提供的 Meshy 资产，授权相互独立。
