# 守寝者：复用百目横扫 V12

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

2026-10-16。用户否定守寝者 V09 挥击，并明确指定采用百目的挥击。按最新 `ue5-monster-workflow/references/hundred-eyed-slag.md` 和百目实际制作链继续。

## 选用内容

百目当前普通横扫入口为 `AttackSweep_R`，原生类引用 `/Game/Monsters/HundredEyedSlag/V1/Animations/A_HundredEyedSlag_AttackSweep_R`。其受认可的攻击主体来源为 Epic Rampage `Attack_Biped_Melee_A`；本轮复用同一完整双足供体及百目 V8 的时间编排，适配到守寝者现有双足骨架，不把百目的四肢撑地姿势直接写入守寝者。

源资产 `/Game/ParagonRampage/Characters/Heroes/Rampage/Animations/Attack_Biped_Melee_A`，模型 `.../Meshes/Rampage`。原源长 1 秒；百目时间映射为 `(0,0)、(0.50,0.23)、(0.73,0.39)、(1.40,1.0)`，括号分别为角色动作秒和供体秒。守寝者采用同一 1.4 秒完整节奏，接触窗口 0.54–0.73 秒，0.48 秒锁定朝向。

## 制作与接入范围

- 原生 IK Rig / IK Retargeter 迁移整身。Rampage 三段脊柱映射到守寝者四段脊柱；肩—肘—腕、髋—膝—踝按对应三个解剖关节 OneToOne。Rampage twist / muscle 骨在主链旁分支，不串入守寝者肘腕链，也不将其扭转额外叠到主骨。
- 保留守寝者原骨长、参考姿态和蒙皮。只做整体朝向注册、净平移去除、脚底基准，以及起收阶段接回现有待机；挥击阶段的肩肘腕和身体旋转保留原生供体结果，不另加 V09 大幅肩部搜索或独立手掌目标。
- 从最终守寝者动作生成前臂/巨掌轨迹与实际可达距离，动画、AI 接触窗口和伤害沿用同一个服务端时钟。
- 保留 V10 显示模型、贴体内衬、连续围布与实尺寸碰撞；保持移动转向和现有待机/行走引用。只更新攻击资产与其配套参数，不重导模型，不新增 C++ 或运行时 IK。

本轮早先准备的 V11 Attack_D 候选因用户指定百目而未接入，不属于游戏当前动作。V09 旧攻击保留为历史输入，不能作为已获认可动作。

## 生产文件和状态

制作根 `SourceAssets/NightWarden20261015/V12HundredEyeSweep`。

脚本：`prepare_hundred_eye_sweep_v12.py`、`author_hundred_eye_sweep_v12.py`、`install_hundred_eye_sweep_v12.py`，后台入口 `v12_background.ps1 -Stage Source/Install`。UE 目标目录放在 `/Game/Monsters/NightWarden/V09Melee/HundredEyeSweepV12`，继续使用已编译的动画完成辅助入口。

原生重定向和离线动作制作已完成。`Records/native_retarget.json` 读取到百目当前原生类的横扫引用为上述 `A_HundredEyedSlag_AttackSweep_R`，时长约 1.4 秒；Rampage 原始双足供体时长 1 秒。已保存专用 IK Rig、Retargeter、原生动作，并生成 60 Hz、85 个采样的最终骨骼轨道与可编辑 `Authoring/NightWarden_HundredEyeSweep_V12.blend`。

最终动作的制作输入给出起手距离约 148.52 cm、停距约 120.52 cm，前臂/巨掌路径按同一动作生成。源供体资产使用 29 fps，最终安装改为新建目标骨架动画再写入 60 Hz 轨道，避免对已有 29 fps 模型直接设置不兼容帧率。

2026-10-16 20:29（Asia/Shanghai）正式动画、骨架依赖和原 `BP_NightWarden` 已实际保存。Source 和最终 Install 后台 commandlet 均退出 0；前一次 Install 的 29/60 fps 兼容错误已通过上述新建动画方式处理。编辑器关闭后采用后台接入，本轮没有重新打开编辑器。

`Records/ue_delivery.json` 的状态为 `hundred_eye_sweep_animation_and_ai_saved`、`complete: true`。正式动画为 `/Game/Monsters/NightWarden/V09Melee/HundredEyeSweepV12/Animations/A_NightWarden_HundredEyeSweep_V12`，实际时长约 1.4 秒。原蓝图已切换该攻击，并保存配套前臂/巨掌轨迹、0.54–0.73 秒命中窗口及起手/停距参数。伤害保留 45，Yaw 转向速度保留 100°/秒，待机、行走和 V10 围布网格引用保留。

旧 V09 动画资产保留，替换前蓝图备份位于 `Records/BP_NightWarden.before_v12.uasset`。用户使用原 F6 守寝者入口重新生成角色即可加载新攻击。

未启动游戏、渲染或验收。百目原攻击主体的认可不自动成为守寝者的动作、穿模或打击感认可；本轮交付后由用户试玩确认。
