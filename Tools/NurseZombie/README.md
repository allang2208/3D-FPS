# 护士僵尸测试接入

项目：`D:/FPS3D/FPSGAME/FPSGAME.uproject`，UE 5.8。

入口：`/Game/GameMaps/L_Normandy_FPS_Test`。独立角色蓝图：`/Game/Monsters/NurseZombie/BP_NurseZombie`。村庄保存两只实例，Outliner 文件夹 `Gameplay/NurseZombieTests`。重新进入地图可恢复两只敌人。

启动：PowerShell 执行本目录 `Open-NurseTest.ps1`；加 `-Audit` 运行自动测试。村庄原 PlayerStart 带近倒置的旋转，本次将其 pitch/roll 归零并保留水平朝向，避免相机在脚下。放置检查包含同层地面、胶囊净空、视线和通路扫掠。

## 来源与动作

用户下载并已导入的 `/Game/ZombieFemale/Asset` 包；本任务未修改原始模型、材质或动画文件。没有找到随包许可文本，来源/许可暂按用户提供素材记录，不自行宣称 CC0 或商业授权。

原有三条动画均为同骨架 AnimSequence，30 fps，待机 10.2667 秒/308 帧间隔、行走 3.2667 秒/98 帧间隔、攻击 3.3333 秒/100 帧间隔（采样关键帧含末端各多一帧）。资产未带死亡动画，死亡复用原 PhysicsAsset 做 ragdoll。

已导出并检查三条源动作的多时刻模型姿态：待机头歪、双臂自然下垂并轻摆；行走左右承重与摆臂不对称；攻击先扭转蓄力，左臂抬起展开，身体前压伴随下挥，随后低身收势并站回。游戏沿用动作，接触窗口暂定 1.40–1.70 秒，单次命中，整个攻击 3.3333 秒后再冷却 0.8 秒。实际动画播放和命中判定由同一个时钟驱动。

游戏动画另存 `A_Nurse_idle/walk/attack`，行走和攻击去除 root 水平累计位移的线性趋势，保留骨骼旋转、纵向运动和相对摆动，避免与 CharacterMovement 双重移动。所有源资产保持原样。FBX 动作导出预览仅用于分析身体姿态；最终外观以 UE 游戏渲染为准。

## 测试数值与行为

- 生命 120；当前 AKM 每发 30，身体命中约四发击杀。
- 伤害 15；警戒 850 cm；出手距离 130 cm，最远命中 145 cm，检查朝向、高差和墙体遮挡。
- 行走 52 cm/s，播放速率按实测位移调整。测试使用可视范围内的直接追击与 CharacterMovement 碰撞，不含跨建筑寻路网络。
- 中弹打断当前动作；死亡立即停止攻击与胶囊碰撞；物理尸体保留 12 秒。
- 玩家生命 100，受伤显示短暂 HP 提示和红色闪屏；生命归零后 2 秒在安全出生点重生。

## 可重现工具

`inspect_nurse.py` 在 UE Python commandlet 中导出源动作，使用 `-AllowCommandletRendering`（该引擎的 FBX 预览导出不能用 `-nullrhi`）。`render_source.py` 用 Blender 生成动作采样图。

`integrate_nurse.py` 创建独立资产、保存村庄实例并检查重载；首次修改前备份在 `Saved/NurseZombie/L_Normandy_FPS_Test.before-nurse.umap`。`verify_saved_nurse.py` 用新进程核对保存结果。

原场景完整运行测试：启动独立游戏并带 `-NurseAudit -NurseCapture`，结果应包含 `NURSE_ACCEPTANCE_COMPLETE failures=0`，各断言与截图在 `Saved/NurseZombie`。该自动测试含人工构造的距离/躲避/伤害夹具和真实 PlayerController 射击输入，不代替完整人工试玩。

## 本次验证（2026-09-09）

- `build7.log`：UE 5.8 Editor Development 编译 Succeeded（后缀模块 9147，兼容并行枪械工作）。
- `integrate-final.log`：`NURSE_INTEGRATION_OK`；`readback-final.log`：新进程重载 `NURSE_SAVED_READBACK_OK actors=2 blueprint_defaults=valid`，PlayerStart pitch=0/yaw=180/roll=0。
- `runtime-final.log`：真实村庄 D3D12 默认渲染下 15 项 PASS，`NURSE_ACCEPTANCE_COMPLETE failures=0`。包括两只保存实例、资源、实际追击位移、落地、玩家血量、接触单次命中、无重复伤害、躲避、打断、真实枪械输入命中、死亡碰撞、ragdoll、尸体移除、死后无伤害及玩家重生。
- `validation-result.json` 为结构化结果；`nurse-front.png` 和 `nurse-ragdoll.png` 为最终游戏画面，已目检。完整村庄人工游玩和跨建筑寻路未验收。
- commandlet 仍报告项目已有的 GameFeatureData 配置错误等全局问题，不能把该进程整体称为零错误；本次资产脚本完成标记、新进程回读和游戏专项断言分别保留。
