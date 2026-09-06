# 工头 V04：四动作协调优化

依据更新后的 `skills/godot-monster-workflow/references/humanoid-motion.md`，先查看原项目四套完整动作参考，重做 Idle、Walk、Attack、Death。Howl 保留 V03。模型身份、材质、33 节固定缩放鞭子骨架与战斗时序保留。

- 攻击：C1 曲线连接起势、扬鞭、抽击、收势；骨盆、胸、头分配不同角度与时差。双臂使用胸部空间目标和统一肘部弯曲平面，手腕跟随前臂。修掉扬鞭时肘部参考方向奇异导致的瞬间翻转，不再用逐段 smoothstep 让每个中间姿态停车。
- 移动：重步交替，支撑相脚向后速度匹配 0.4301075m/s；摆动相首尾切线匹配支撑速度，抬脚落地竖直速度归零；胸胯反向小幅摆动，手腕滞后。游戏速度 0.65m/s 对应约 1.51 倍播放。
- 待机：轻微呼吸、胸胯和手臂小幅错峰，保留 1 秒周期。
- 死亡：屈膝、坐倒、背部接触、头臂迟滞、错峰伸腿；终帧躺倒，保留 1.4+1+.3 秒业务合同。
- 落地：按变形网格最低点在世界竖直轴修正根骨，修复旧脚本把根骨 local Z 当世界 Z 的问题。
- 切换：复用当前 ordinary_zombie.gd 已有显示姿态混合，测试确认工头攻击/死亡承接当前姿态，业务时钟不延迟。没有改动该共享控制器。

## 重建与验证

输入：`../foreman-v01-20260906/foreman-arm-v03.blend`。Blender 后台运行 `build_motion.py`，输出可编辑 `foreman-motion-v04.blend` 和 GLB；`check_motion.py` 重新导入 GLB 检查循环、脚底和步速；Python 运行 `check_export.py` 对实际导出蒙皮检查；Godot 运行 `render_motion.gd` 获取默认 D3D12 实际渲染，再用 `package_preview.py` 打包四动作和游戏步速预览。

正式场景 `scenes/enemies/foreman_zombie.tscn` 已切至 `assets/models/foreman_zombie/foreman_v04.glb`。

证据：`review-report.json`、`export-validation.json`、`tests/test_foreman_motion.gd`。模型未增加逐指骨骼，握持细节仍受现有手掌网格限制；本轮优化的是完整动作协调性，未声称完成动捕或已获用户自然度验收，视觉效果待反馈。默认灯光下的阴影间隙另以 Godot 实际蒙皮最低点校验，未用灯光掩盖落地。

## 本轮验收结果

- 正式工头行为 24 项通过；动作连续性/循环/脚速/实际移动/切换 8 项通过。实际追击 90 物理帧移动 0.964 米，角色保持落地；Godot 导入后的支撑脚速度误差峰值 0.0172m/s。
- 导出后重新导入：Idle/Walk 首尾矩阵误差为 0；身体最低点约 4.4–8.5mm。Godot 对 Idle、攻击接触、Death 终帧直接计算蒙皮最低点也约 5mm。
- 60Hz 身体关节相邻帧转角最大 0.304rad；修复前曾检测到右前臂/手腕相邻帧约 2.05rad 翻转。鞭子实际 GLB 在 1349 个采样姿态内无异常放大。
- 主场景 180 帧冒烟完成。combat/reload 业务断言通过，但旧仓库面板夹具报错及部分退出资源告警仍在；不将整个项目日志描述为零错误。动作测试使用独立场景，避免并行 UI 构建影响动画证据。
- 默认 D3D12 Forward+ / GTX750Ti 实际渲染四个动作、攻击/死亡正侧面以及 1.51 倍游戏步速。预览未做 AI 增强；GIF 死亡额外保留 1 秒，循环只为展示。未执行用户完整人工通关试玩。

预览：[攻击](Attack.gif) · [移动](Walk.gif) · [游戏步速](WalkGameSpeed.gif) · [死亡](Death.gif) · [待机](Idle.gif)。
