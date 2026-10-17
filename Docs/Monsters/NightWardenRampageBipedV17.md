# 守寝者 V17：Rampage 双足重步（2026-10-17）

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

> 用户否定本版的僵硬与滑步，要求排查重定向链路。后续修正和证据见 [V18 联动与支撑脚修正](NightWardenCoupledLocomotionV18.md)。下文保留 V17 历史制作记录，不表示用户认可。

用户截图否定 V16：躯干前倾过深，动作像鞠躬走路。V16 原生输出的头部相对骨盆倾角约为 60–62 度，周期变化很小；该版不能作为已认可移动模板。

## 动作与体型适配

改用现有工程中的 `/Game/ParagonRampage/Characters/Heroes/Rampage/Animations/Jog_Biped_Fwd`。这是百目挥击同源 Rampage 的完整双足移动，源循环为 1 秒；未调用生成服务。供体逐帧数据保留在本机，不将其视为可自由公开的开源素材。

制作保留 V14 裸身、左手修复和原 46 骨结构。UE 原生 IK 链映射完整躯干与四肢，三关节臂腿使用 OneToOne；原生输出单独保留在 `V17RampageBiped/Motion/native_walk.json`。

- 肩背和头颈七根骨的平均旋转回到 V08 站立待机基准，保留供体围绕平均姿态的周期变化；不把躯干冻结成单一姿势。
- 保留源骨盆移重、屈膝和交替迈步；完整周期调整为 1.4 秒、60 FPS、85 个采样点。
- 右侧巨臂的锁骨、上臂、前臂、手腕及手指一起滞后 0.077 秒，保持同一骨链相位及关节关系。
- 按原脚底蒙皮制作接地；源为原地动画，不用首末帧的零位移推断朝向或移动速度。
- 双脚支撑段拟合出的动画速度基准为 141.7931 cm/s。安装时同步 `SourceWalkSpeed`、`WalkSpeed` 和 `MaxWalkSpeed`，保留现有按实际速度及角色缩放调整步频的逻辑。

## 保存状态

源数据、原生重定向资产、可编辑身体适配源、最终动画和原 `BP_NightWarden` 均已保存。`SourceAssets/NightWarden20261015/V17RampageBiped/Records/ue_delivery.json` 记录 `complete=true`，当前蓝图已由 V16 切换到 V17；后台安装命令退出码为 0。

首次最终安装因 PIE 被脚本阻止，没有替换活动动画；用户确认停止后继续完成后台保存。最终时长约 1.4 秒，`SourceWalkSpeed` 与 `WalkSpeed` 均为 141.7931 cm/s，转身 Yaw 仍为 100 度/秒。可从 F6 原守寝者入口重新生成角色体验。

未启动游戏、截图或渲染验收；游戏表现待用户体验。现有 V08 待机、V12 百目挥击、转身设置与裸身模型保持原引用。

## 制作与恢复

制作目录：`SourceAssets/NightWarden20261015/V17RampageBiped/`。

重建脚本位于同级 `Scripts/`：

1. `read_biped_source_v17.py`：读取现有供体原始动作。
2. `v17_background.ps1 -Stage Retarget`：原生重定向与逐帧输出。
3. `author_rampage_stride_v17.py`：姿态中位、巨臂相位、循环和脚底适配。
4. `v17_background.ps1 -Stage Install`：保存独立动画并更新原蓝图。

目标动画为 `/Game/Monsters/NightWarden/V07WaistStride/RampageBipedV17/Animations/A_NightWarden_RampageBiped_V17`。编辑源为 `Authoring/NightWarden_RampageBiped_V17.blend`，动画轨道为 `Motion/rampage_keys.json`。安装前蓝图备份为 `Records/BP_NightWarden.before_v17.uasset`；不覆盖历史制作记录。
