# Kwang 第三人称握剑与旋风方向调整

**2026-10-10 刃口方向追查：唐刀既有的柄轴 180° 安装旋转与通用剑刃口基准不同。曾仅将全局转向改为 -720，用户实机反馈方向错乱，已撤回该改法；当前保持 +720，并单独处理唐刀旋风刃面和角色朝向同步。见 [唐刀旋风修订](third-person-tang-dao-whirlwind-20261010.md)。**

**2026-10-10 状态更新：V3 的腕部／肘极优化造成裸臂折叠回归，已由独立恢复资产替换六项运行引用。本文保留历史制作记录，不能再把 V3 的接触数据检查当作动作认可。当前制作与接入见 [近战折臂修复](third-person-melee-arm-recovery-20261010.md)。**

用户已认可 2026-10-06 的 Kwang 全身动作，本次保留躯干、髋部、脚步、动作切段和接触时序，只调整双臂握持与旋风转向。

## 制作与接入

- 制作源：`SourceAssets/ThirdPersonSwordGrip20261007/refine_kwang_grip.py`，输入上一版 `ThirdPersonSwordKwang20261006/adapted-actions.json`，输出独立版本。
- 手掌绕圆形握柄选择连续握持角度，肘部保留原动作的运动平面偏好；双手超出可达范围时共同平移，不再分别截断手腕目标。
- 前臂主骨保持肘关节弯曲平面，旋前／旋后按 Jason 辅助扭转骨的实际位置分配。上臂辅助骨和肩部辅助骨同步处理，避免叠加旧重定向的扭转。
- 右手 `SwordGripRoll` 曲线与动作骨骼一同混合；身体最终骨骼完成后，第三人称剑根围绕原生 `WPN_root` 反向补偿握柄转角，使手掌调整不改变已认可的剑刃朝向。
- 六个独立资产目标：`/Game/Characters/JasonPlayer20261003/KwangSwordGrip20261007/Animations`。旧 V2 资产保留。
- 旋风 `turnDegrees` 由 -720 改为 +720，与 Kwang D 横斩方向一致；配置、类型默认和读取回退值同步更新。圈数、持续时间及伤害数值不变。

## 落盘过程

`Tools/PlayerBody/save_kwang_sword_grip.py` 保存六段动画和曲线；后台保存结束且原生构建成功后，运行 `publish_kwang_sword_grip.py` 更新 `player_body.json` 的六个 `Melee.FullBody.*` 引用。保存与发布回执位于制作源目录。

六段资产已由后台 Python commandlet 保存，退出码 0，日志为 `SourceAssets/ThirdPersonSwordGrip20261007/save-commandlet.log`；无需打开编辑器界面。

Editor 原生模块构建成功，日志为 `Saved/BuildEditor/build-20261007-002641.log`。六个动作引用已发布到 `Content/ColdSteelData/player_body.json`，发布前引用记录在 `SourceAssets/ThirdPersonSwordGrip20261007/assets-published.json`。

本轮未运行游戏、截图、渲染或测试，动作效果由用户体验。

## 用户要求回查后的修正（2026-10-07）

本节为后续显式检查，不将上一轮仅编译完成视为动作验收。

发现并修正：

1. 握柄转角逐帧展开会累计至 580°，退出包络直接乘回零，造成最高约 115°/帧的反拧。改为整段路径选择，首尾回零，并约束相邻握角；60 Hz 制作阶段最大约 21.43°/帧，最终 120 Hz 资产最大约 10.72°/帧。
2. 肘极的有符号角在 ±180° 处被硬截为 ±105°，会瞬间换边。取消该截断，以连续方向及相邻肘位代价选择轨迹。
3. 将累计的完整 360° 直接按辅助骨比例分摊，会在收势留下约 120.24° 的辅助骨残留。改为周期性轴向旋转混合，在分配后的辅助骨自身旋转上平滑；本批首尾骨骼旋转差小于 0.001°。
4. 原保存脚本仅按日期跳过已存在资产，重新制作后可能沿用旧数据。最终新包使用独立 `KwangSwordGrip20261007V3/Animations` 目录，并按制作数据散列判断同批续接；发布要求六段全部保存完成且制作数据版本相符。
5. 保存时只调用 `SetFrameRate(60)`，未完成模型 `NotifyPopulated`，导致 UE 的压缩目标仍为默认 30 Hz。首次压缩数据读回出现最大约 4.87° 曲线偏差及 4.30 cm 双手接触误差。给现有 `WeaponAnimationAuthoring` 增加最小原生收尾接口，将制作模型的采样率同步到压缩目标；Python 保存脚本统一调用该接口。
6. 恢复 60 Hz 后，关键帧之间的独立骨骼插值仍有最大约 1.64 cm 的握点残差。补烘焙中间接触到 120 Hz：原帧与身体动作保留，中间姿态只修正双臂的共同可达范围与握柄接触；时长和接触标记不变。

检查工具：`Tools/PlayerBody/audit_kwang_grip_data.py --require-fixed`。已执行骨段长度、躯干/腿部保持、四元数有效性、双手握点、旋风分段接点、收势闭合及握角跳变检查。源数据中双手握点残差小于 0.001 cm；该数值是刚体骨骼接触误差，不代表手指蒙皮或衣物无穿插。前后报告位于制作源目录的 `grip-data-audit-before.json` 和 `grip-data-audit.json`。

运行时复查：`SwordGripRoll` 随动作姿态混合，UE 在最终骨骼回调前更新曲线，武器围绕原生剑根反向补偿；旋风配置、默认值与缺省读取均为 +720°。运行时补偿逻辑沿用上一轮，本轮 C++ 仅新增编辑器资产制作收尾接口。尚未运行 PIE 或画面验收，极限姿态的自然度仍待实机确认。

最终交付：六段 V3 资产按 120 Hz 保存并发布；独立 commandlet 从磁盘读回压缩姿态，以 240 Hz 检查帧间接触。最大握点残差约 0.62 cm，曲线误差小于 0.001°，骨架、版本散列、Contact/Release/NativeSwordGrip 标记及六项配置引用匹配。残差不是零，骨骼数据检查不代替手指和衣物画面验收。

原生构建：`Saved/BuildEditor/build-20261007-011844.log`（成功）。保存：`save-review-120hz.log`；资产读回：`readback-review-120hz.log`；汇总：制作源目录 `review-complete.json`。没有启动编辑器界面或游戏。
