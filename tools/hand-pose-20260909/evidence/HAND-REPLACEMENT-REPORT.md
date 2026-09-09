# 六款枪械手模替换与动作复查 — 2026-09-08

后续连续切枪与动作打断检查、发现的两类遗漏及修复见 [打断动作复查](INTERRUPTION-AUDIT.md)。该报告补充了本页尚未覆盖的连续输入测试。

本轮已将六款枪械的双手替换为逐骨架适配的正式资源：AK-105、AKM Classic、HK416、QBZ191、M16、P9。当前游戏从 `E:/3d/3-dfps/assets/models/player_hands/free_fitted_v1/` 加载。此前仅 AK-105 候选、掌心独立补片和“尚未正式替换”的记录均为历史版本。

## 实际改动

- 每款枪分别使用自己的原骨架、绑定顺序和动画库，保留原袖子，移除原手部三角面，避免新旧手模叠在一起。
- 用连续网格重建掌部体积，修正原拟合造成的中间凹陷；重新处理拇指根部权重及掌指过渡，指尖、指甲和手套开口保持独立细节。最终方案未使用分离的掌心补片或运行时体积着色器。
- 修正肤色、粗糙度、皮肤和指甲贴图；手套使用深橄榄色。贴图随资源内嵌，修掉资源保存时袖子贴图引用丢失的问题。
- 左侧伸出的侧斜握把使用 `canted` 的独立握持坐标。大弹鼓换弹末段按对应源动画收手时刻回握，腕部移动与手指闭合重叠，取消多余的先上抬再落下动作。握稳后弹鼓避让不再推开手腕。
- 复查发现空枪动作、装备、收枪和检视的原厂支撑姿态可能穿过新增握把。现在在释放阶段按实际配件包围范围做平滑侧向避让，保留源手腕朝向；换弹路径仍走专用回握逻辑。
- 修掉 HK416 / QBZ191 独立手腕骨骼分支造成的袖口脱节：上臂转动后，以实际前臂末端解算，而非仍留在旧位置的独立手腕；超出手臂可达范围的目标同时约束手腕位置。握把和弹鼓避让共用这一修正。

## 检查证据

| 检查 | 结果 | 证据 |
|---|---|---|
| 六款枪、原厂/四种握把、标准/大弹鼓、全部可用动作 | 530 个配置动作组合，无记录失败；逐帧检查骨骼，关键阶段渲染第一人称及左右手近景 | `animation-v6-results.json`、`animation-review.log`、`animation-v6-review/` |
| 五款步枪普通/空仓换弹，四握把，30/60/144 帧与不同速度/ADS | 240 组通过；稳定回握最大位置误差约 0.231 mm | `final-contact.log` |
| HK416 / QBZ191 袖口连续性，全部动作与握把/弹鼓组合 | 176 组通过；物理前臂末端与独立手腕最大差约 0.192 mm | `cuff-test.log`、正式测试 `tests/test_hand_cuff_continuity.gd` |
| 正式资源、骨骼绑定、权重、贴图、旧手移除、配件拆装保持新手 | 六款通过；检查 1,102,320 个手部顶点条目（含接缝重复顶点），六资源均无外部资源依赖 | `final-resource.log`、`tests/test_fitted_player_hands.gd` |
| 实际 Gun 加载、六枪切换、原厂/侧斜握把大弹鼓、腰射/ADS、空仓换弹 | 六款通过；ADS 标记与相机对齐、弹药守恒、换弹完成及新手资源身份检查通过 | `gameplay-preview.log`、`gameplay-final/` |
| 五枪侧斜握把大弹鼓实际换弹业务 | 普通/空仓，30/60/144 帧：时长、容量、弹药守恒及机械挂点检查通过 | `final-gameplay.log` |
| 切枪缓存、配件身份、隐藏实例与贴图复用 | 通过 | `final-switch.log` |
| 可编辑源保存并重新打开 | 六套 GLB/BLEND 均完成；保留各自原动画动作 | `editable-v6/editable-check.json` |

530 个组合覆盖各枪实际存在的 idle、aim、fire、aim_fire、reload、reload_empty、inspect、draw/equip、equip_charge、equip_quick、holster、empty；并非每款源模型都有同名动作。排除 RESET 和重复生成的 drum 动画条目，弹鼓通过实际换弹调用验证。

渲染使用实际模型及最终资源，不是生成图片。关键动作图按 10%、40%、70%、98% 阶段采样；完整换弹预览由实际 Gun 每两帧一次的 30 FPS 渲染组成，以 15 FPS 播放，最后加 0.4 秒预览停顿。全体动作图已逐枪浏览，对发现的握把穿手、袖口脱节进行了重新渲染验证。数值检查与这些视角的视觉复查不等于任意输入打断组合下的逐三角面碰撞证明。

## 预览与可编辑交付

- [六枪实际持枪预览](gameplay-final/all-six-hands.jpg)
- [AK-105 侧斜握把与大弹鼓换弹](gameplay-final/infima_ar-reload.gif)
- [AKM 换弹](gameplay-final/akm_classic-reload.gif)
- [HK416 换弹](gameplay-final/hk416-reload.gif)
- [QBZ191 换弹](gameplay-final/qbz191-reload.gif)
- [M16 换弹](gameplay-final/m16-reload.gif)
- [P9 换弹](gameplay-final/infima_handgun-reload.gif)
- 可编辑源：`editable-v6/{infima_ar,akm_classic,hk416,qbz191,m16,infima_handgun}.{glb,blend}`。

运行时采用原动画加程序化配件适配；导出的可编辑文件保留源动画，程序化修正在 Godot 脚本中，并未误称全部烘焙进 Blender。

## 来源与复现

手模作者 NadevayNoski，来源与记录的许可标识见正式资产目录中的 `CREDITS.md`。下载源及贴图压缩包保留在 `source/`。不是 CC0，也未送入生成服务。

最终生成器 `fit_hands_v6.py` 按 `HANDS_WEAPON` 选择六款枪，骨架输入来自 `export_hand_rigs.gd` / `hand-rigs.json`。`assemble_hands_v3.gd` 将各枪自己的袖子和 v6 手网格组装进 `prepared-v3/*.res`，正式目录使用其副本。文件名中的 `v3` 为历史中间命名，不能据此选用更早的候选或 `fit_candidate.py`。`export_editable_hands.gd` 和 `save_editable_all.py` 生成并检查可编辑交付。

## 运行边界与日志

所有检查使用独立存档/设置路径，未改玩家存档。系统根证书读取错误在本机原已存在；无头资源检查的虚拟渲染器有空材质查询日志，切枪测试有着色器缓存写入警告。相关通过结论依据实际断言和完成标记，不将退出码单独当作通过。本轮最新实际 Gun 渲染日志有完整六枪通过标记。

当前是本地正式接入，未做远端发布或提交共享工作区的其他改动。新手资源测试与袖口回归测试已经留在正式项目；原源 GLB 和历史失败对照保留。
