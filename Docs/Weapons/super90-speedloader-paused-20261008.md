# Super90 快速装填：暂停与待办（2026-10-08）

> 历史记录：最新状态与恢复入口见 [2026-10-12 整理发布](super90-publication-20261012.md)。当前为 R24 姿态＋R25 播放节奏，普通空仓 R2、近战 R9；下述暂停与“当前版本”只代表当时状态。R10/R11/R13/R18 源及本轮旧回滚副本已归档，按最新逐文件清单恢复。

状态更新：**R18 换弹被用户否定，当前已[恢复 R17](super90-restore-r17-20261009.md) 完整动作及原音画时钟，14 个动画与四份握把配置已保存，Editor/Game 编译完成。60 ms 射击间隔独立保留。后续应保留动作原速与全过程，仅更早掏出并消除阶段间等待；该新节奏尚未另行实施。下文保留历史记录。**

## 2026-10-09 R10 复检：仍不合格，继续暂停

R10 已按 [R10 方案](super90-speedloader-r10-plan-20261009.md) 在 `SourceAssets/Super90LoaderR10_20261009/` 后台制作并保存 24 项资产，**替换了本页所述 R9 的同名正式资产**（R9 旧包备份在 R10 的 `Before/Content/`）。用户实机体验后判定整体仍不合格，R10 不是认可版本。

### 参考源（记入备查）

- **主动作参考**：用户自录《三角洲行动》M1014 装填器**空仓**换弹，`C:\Users\allan\Videos\NVIDIA\Delta Force\Delta Force 2026.10.09 - 09.55.46.01.mp4`（7.83 s、2560×1440、60 FPS；装填段约 2.8–5.4 s）。拆帧在本机 `D:\FPS3D\test\super90_df_ref\`（`frames60\` 全帧、`overview\` 分段拼图），仅本机使用、不发布。
- **始终缺失**：非空仓（打几发再装）的第一人称装填器参考至今没有拿到；R10 普通换弹收尾是从空仓段推断的。
- **旧 B 站参考**：`SourceAssets/Super90MotionRevision20261007/Reference/reference_video.m4s`（BV11wTe6sEsS，480P，装填段 40.63–42.50 s），目录被 gitignore 排除、始终未能看画面，未用于制作。
- **第三人称机理**（只可观看，不能提取）：Jerry Miculek 高速慢放 <https://www.youtube.com/watch?v=xXkyEbrqNGw>（TEC Loader＋Arredondo 漏斗，Mossberg 930）。
- **结构依据**：Arredondo 装填漏斗（M2 款可装 M4，<https://www.speedshooter.com/product/arredondo-speedloader-funnels/>）；专利 US4509284A（管身开槽、握钮经连接板穿槽）；TEC Loader 管＋握钮结构。
- R10 的作者渲染自检拼图（非实机）：`D:\FPS3D\test\super90_r10_diag\`（`v9` 普通、`v9e` 空仓、`v9b` 修订后抽查）。

### R10 当时已做（仍被判不合格）

- 托底为支点的侧倾（46°→66°）＋抬枪口 30°；280 mm 短管，推送全程在画面内；取管期间手完全出画。
- 圆柱握钮＋穿槽连接板、贴合机匣的低轮廓漏斗、阻尼冲击层（撞管/逐发咔哒/末发重坐/回握拍击）。
- 空仓为左手从机匣下方勾拉拉机柄（`empty_mode='rack'`），枪机末发+48 复进；右手食指按压路径保留为备选。
- 手臂解算：连续肘向、自然前臂轴、蒙皮扭转增量续传限速并末段收敛（斜握把族的取管拧臂已按数值修复）。
- 改造图标仍是旧装填器外观，未更新。

### 恢复时的注意事项

- R10 作者入口与定稿参数：`SourceAssets/Super90LoaderR10_20261009/README.md`；全部脚本、求解器、渲染器在该目录，别重跑 R9 的 `../Super90Speedloader20261007/author_speedloader.py`。
- 待机输入仍是 `Super90IdleMatchWalk20261008` 的已装 idle，R10 不导出、不覆盖它。
- C++ 改动只有 `Super90SpeedloaderAssets.h` 空仓复进时刻（+44→+48）。
- 任何恢复都先和用户确认方案与验收口径；不把离线渲染、诊断数字或“资产已保存”当作合格证据。

## 尚未解决

- [ ] 快速装填的完整动作仍需重做或修正：取出、对接、推入、松手、脱离、回握必须连续自然，不能用线性位移或手腕单独转动掩盖肘腕问题。
- [ ] 左手掌、指根、拇指、小指与装填器／连接件的穿模：后续环抱握姿候选仍在松手、退让阶段出现相交；不能称为消除穿模。
- [ ] 装填器和通用前握把的真实抓握：部分数值上无相交的候选实际为“握空”，已判定不能采用。必须同时满足掌心、指腹接触和自然指形。
- [ ] 通用前握把持握、离握和回握：vertical（含 tactical_vertical）、canted、prism、angled 的旧持握存在指根／掌侧交叠；各拟合候选均未形成可接受定稿。
- [ ] 手臂稳定性、前臂扭转和可见性：保留原生骨段长度，避免错误弯折；枪托、手臂不能遮挡装填细节。
- [ ] 动作与镜头抖动的配合：检查接触、推入止点、空仓释放和回正的节奏，不以曲线计算或事件对齐代替最终观感。
- [ ] 最终方案才重新导出、导入、保存并按当时用户授权范围检查；裸手、装备外观、各装填数量、空仓与非空仓、打断分支需明确各自覆盖范围。

## 暂停时的真实资产边界

1. R9 第一批已经实际保存 21 项资产：15 份装填／cycle 动画、基础 idle、装填器道具网格、4 份前握把 profile。记录在 `SourceAssets/Super90ContactR9_20261008/import_receipt.json` 和 `import_bridge_01.txt`。**保存成功不代表动作合格，这批同样没有用户认可。**
2. 随后继续修改了作者源、环抱握姿、松手指形和连接件；这些最新修改**尚未重新完成正式导出和 UE 导入**。当前 `hand_fit.json`、`prop_geometry.py` 和作者脚本与上一批已保存资产不一致，不要直接重跑导入脚本当成最新结果。
3. 前握把 `grip_hand_*.json`、`fit_foregrip_*.py`、`fit_grip_*.py` 为探索候选，未正式应用到 profile；包括 `grip_hand_encircle3d.json` 在内，都不能当作通过的姿势。
4. 之前的“729 个已保存姿势无相交”只覆盖当时的枪身／导入口／装填器，不含实际前握把、衣袖装备，也不覆盖随后改过的作者源。它不能证明整套动作不穿模或视觉合格。
5. 本轮未启动 PIE／游戏；离线诊断帧与 GIF 不能冒充实机结果。暂停时没有发现仍在运行的本任务 Blender／Python 制作进程。
6. 曾尝试的镜头回正一行 C++ 修改已撤销；完整构建被其他模块错误中断，本轮没有新的镜头原生修改等待交付，不宣称项目构建通过。

## 保留入口

- 当前作者源：`SourceAssets/Super90Speedloader20261007/author_speedloader.py`。
- 制作现场、拟合候选和诊断：`SourceAssets/Super90ContactR9_20261008/`。
- 第一批导出／保存记录：`authoring.json`、`import_receipt.json`、`Diagnostics/saved_assets.json`；当前作者源已发生后续变化。
- 抓握修改前对照：`hand_fit_before_encircle.json`；随后环抱候选：`hand_encircle.json`、当前 `hand_fit.json`。
- 仍有相交的最新环抱候选记录：`check_encircle_full2.log`。`Diagnostics/full_contact.json` 等通用文件会被后续试验覆盖，恢复时须按对应源版本解释。
- 导入前恢复材料：`trash/super90-retired-20261009/SourceAssets/Super90ContactR9_20261008/Before/`；未获用户要求，不执行回滚。

恢复开发时先明确采用的动作方案和实际当前资产，不把任何被否定的版本登记为成熟案例；保留普通逐发装填、配件、音效与其他并行工作。

## 同日独立待机修订（快速装填仍暂停）

用户随后认可移动状态的左手持枪，单独要求把待机调整为同一握姿。已从实际安装的 walk 动画及其四类前握把配置提取完整左臂，按枪身相对关系迁入 idle，保留原待机时长、枪身和右臂。一个 idle 动画及四个 profile 的 idle 条目已后台保存；移动、其他动作和快速装填暂停现场均未改动。未运行游戏测试，由用户体验。制作／保存记录见 `SourceAssets/Super90IdleMatchWalk20261008/README.md` 与 `save_receipt.json`。

恢复快速装填时，应以这次独立修订后的 idle 为待机输入；不要用 R9 旧导出或暂停中的作者脚本覆盖它。此项不代表快速装填、前握把全部动作或穿模问题已解决。
