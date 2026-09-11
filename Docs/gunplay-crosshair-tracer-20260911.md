# Godot 准心、腰射散布与 UE 曳光

## 当前参数：再次增大基础腰射

本轮验证：模块 `UnrealEditor-FPSGAME-9110934.dll` 编译成功，新进程 `Saved/BallisticPresentationAudit-20260911082356.log` 15 / 15 通过，已查看更新后的静止准心截图。

用户再次要求增大，将基础项从 0.0125 提至 0.0175，最终静止半范围从 0.025 增至 0.035（增加 40%）。无配件、无 bloom 时，10 米处静止每轴最大偏移 35 cm，正常移动稳定后 75 cm；腾空和连射参数沿用上一轮。准心继续匹配真实投影边界，ADS 零随机。

## 最新调整：强化腰射精度惩罚

验证：`UnrealEditor-FPSGAME-9110927.dll` 编译成功；独立进程 `Saved/BallisticPresentationAudit-20260911082053.log` **15 / 15 通过**，包括实际按住腰射后 bloom 累积检查。已查看本次 `Saved/BallisticPresentationAudit/01-hip.png`，静止准心明显扩大。

用户要求腰射惩罚更明显，覆盖下方旧参数：当前最终角度半范围为 `2 * (0.0125 + bloom + move + air) * 配件倍率`。无配件、无连射累积时，10 米平面上静止每轴最大偏移 25 cm；5 m/s 移动达到稳定后为 65 cm；静止腾空达到稳定后为 75 cm。保留原版两个轴独立均匀采样和准心投影匹配。

移动额外项按速度（m/s）乘 0.004，上限 0.020；腾空额外项 0.025。腰射每发增加 bloom 0.003、上限 0.018；最后一发之后 0.18 秒开始按 0.018/s 恢复，满 bloom 约 1.18 秒回到基础值。此前每发 0.0012、恢复 0.12/s，导致正常射速下几乎不累积，本次修正这一体验。ADS 不增加腰射 bloom，射击方向继续零随机。

## 后续调整：默认散布 ×2，准心匹配着弹范围

用户后续要求覆盖下方首轮记录中的散布倍率和准心间隙公式：腰射最终半范围改为 `2 * (0.0025 + bloom + move + air) * 配件倍率`，静止默认值为 0.005。ADS 仍为零随机散布。

四线样式不变，内侧边缘由当前相机投影矩阵将散布左右/上下极限转换到 HUD 坐标得到，取消旧固定间隙与 28 单位上限。视野角度、视口尺寸、UI 缩放及移动散布改变时，显示边界同步改变。上下、左右分别代表原版方形随机采样的两个轴向边界；准心反映当帧射击范围，不追踪已经飞出的旧子弹。

新增运行检查：2048 条射线投影落在准心内侧边界内并覆盖至少 98% 的两轴范围；同时检查默认翻倍、UI 缩放、移动时不截断和 ADS 零随机。

本次编译 `UnrealEditor-FPSGAME-9110821.dll` 成功。独立运行 `Saved/BallisticPresentationAudit-20260911080229.log` 为 **14 / 14 通过**，已查看本次 `01-hip.png` 实际 HUD。下方 12 项及视频是首轮历史记录，本次未重新录制视频。

2026-09-11，宿主 `D:/FPS3D/FPSGAME`。本次按用户确认从归档 Godot 移植准心，ADS 零散布以本次明确要求覆盖旧资源的 0.2 倍 ADS 散布。

## 来源与最终行为

实际可读归档为 `E:/3d/trash/repository-ue5-root-20260910`。参考 `ui/status_bar.gd`、`ui/style-config.json`、`ui/style.gd`、`scripts/gun.gd`、`weapon_data/akm_glb.tres`，并查看 `docs/preview/ui_crosshair_fixed.png`。

- 四线空心准心：1080p 参考长度 9、半宽 1.5、间隙 `4 + clamp(total / 0.035, 0, 1) * 24`。使用归档 cold_steel 主题实际生效的白色，按视口高度缩放。ADS、背包、仓库、鼠标菜单和翻越时隐藏。绘制归现有 HUD 所有，不截获输入。
- 腰射沿相机左右、上下方向分别均匀随机取值，半范围 `(0.0025 + bloom + move + air) * 已安装配件散布倍率`。原版每发 bloom 0.0012、上限 0.018、连续恢复速度 0.12/s；移动以米/秒乘 0.6、上限 0.012；腾空上限 0.015。准心读同一份运行状态。
- ADS 在随机数分支前返回瞄具方向，包括进入 ADS 过渡。铁瞄读取实际前准星，AKM 使用已有实测校准点，全息读取已有瞄点。射击在重启动画和添加新后坐力之前取样；保留现有后坐力系统。
- 保留相机选点、枪口向目标汇聚以及相机到枪口的遮挡检查。移除飞行子弹目标的额外 2 cm 方向偏移。
- 飞行子弹逐段扫掠后提交实际可见段，命中处截断。暖黄色发光圆柱使用现有 64 槽特效池，单段最多 140 cm、直径 0.65 cm、淡出 0.035 秒。材质正常深度测试，不穿墙显示；视觉不改变伤害、穿透或飞行速度。旧 hitscan 分支也显示曳光。

## 文件与素材

新增 `Source/FPSGAME/UI/ColdSteelCrosshair.cpp`；逐块修改 Character、CharacterProfile、Ballistics 和 WeaponFX；保留这些共享文件原有并行改动。

`Tools/AssetPipeline/build_ballistic_tracer.py` 生成 `/Game/Weapons/GunplayFX/M_BallisticTracer`。材质为本次程序化创建，几何复用引擎基础圆柱，无外部图片或新增第三方素材。二进制留在本机 Content；可用脚本重建。

## 验证

- Editor Development 编译成功，最终本次模块 `UnrealEditor-FPSGAME-9110754.dll`；新独立游戏进程实际加载。没有关闭或重载用户已有编辑器。
- `Saved/BallisticPresentationAudit/assertions.log`：12 / 12 通过，包含 512 次腰射边界、512 次 ADS 零随机、配件倍率、动态准心上限、瞄具偏移、实际命中与子弹停止；最终运行生成 144 段曳光。
- `Saved/WeaponHandlingAudit/tracer09110800-runtime.log`：42 / 42 通过，覆盖配件后坐力、稳定性、存档恢复和帧率无关回稳。
- 实际渲染查看 `Saved/BallisticPresentationAudit/01-hip.png`、`02-hip-tracer.png`、`03-ads.png`。`gunplay-preview.mp4` 是同一最终进程的无声 60 Hz 固定步长画面，不是性能基准；189 张截图中，命名截图占用的帧以此前截图保持相应时长。
- `Tools/AssetPipeline/run_ballistic_presentation.ps1 -CaptureFrames` 可复跑，使用独立存档；截图输出在上述专项目录。
- 原有 `run_gunplay_acceptance.ps1` 本轮 36 通过 / 13 失败，详见 `Saved/GunplayUpgrade/crosshair-tracer-09110757/assertions.log`。该脚本仍在 `DayNight_Lighting` 做有限备弹/不足备弹断言，而当前 `HasInfiniteReserveAmmo()` 明确对此地图返回 true；同时复用了 AuditSession 存档。失败涉及射速、换弹结算、近墙测试未实际出弹、特效清空和声音计数。本次没有修改这些既有测试或将该全流程记为通过，也未对每项失败做基线归因。
- 材质生成 commandlet 退出码 1，但记录 `BALLISTIC_TRACER_MATERIAL_OK` 并保存资源；错误为 GameFeatureData 配置和 8000 端口占用。后续新游戏进程中的真实曳光已验证资源可用。

原有已打开编辑器若仍持有旧 DLL，需要重启后加载本次原生代码。未提交或推送共享工作区的其他改动。
