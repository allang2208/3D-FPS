# 冲刺攻击迁移 · 2026-09-20

2026-09-21 群怪卡顿反馈、针对性优化及构建状态见 [卡顿排查记录](dash-attack-hitch-20260921.md)。

当前阶段：已取消新增前冲及回弹，命中扇区为前方60°（左右各30°）；2026-09-21 最新按用户要求，在就绪后左键攻击时增加0.25秒冲刺持剑转下劈的前摇，替代此前瞬发入口。最新交付状态见 `SourceAssets/MeleeSprintAttackWindup20260921/README.md`。未运行游戏、测试、静态检查、预览或验收。

## 原项目依据

源项目只读：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev`。

- `data/skills.json: skills.dashAttack`：被动，最高 20 级；不是快捷栏主动技能。
- `src/config/dash-attack-config.js`、`src/entities/player/update.js`：连续有效奔跑就绪后左键，停跑／反向／耗尽重置。
- `src/entities/components/dash-system.js`：位移缓出、遇阻回弹、固定方向与扇区、目标去重、基础物理下劈结算。
- `src/ui/skill-manager.js`：命中／多目标／直接击杀修炼，`100×当前等级` 升级。
- 原 `stunDuration=500` 只被另一条突刺分支消费，基础下劈没有眩晕。`cooldownReduction` 虽在旧详情展示，但基础下劈入口没有独立冷却计时；此处按实际行为迁移，不增加虚构效果。
- 火焰与多段突刺为原武器专属变体，不属于本次已制作的基础下劈动作模组。

## 数据与操作

| 项目 | 接入行为 |
| --- | --- |
| 触发 | 持有支持现有近战动作的兵器，地面连续向前奔跑，就绪后左键。体力条上方显示准备百分比和就绪提示 |
| 就绪时间 | `1×(1−(等级−1)×0.03)` 秒；1级1秒，20级0.43秒 |
| 伤害 | `floor(当前武器伤害×(1.75+等级×0.05))`；1级1.80倍，20级2.75倍；沿用共用武器暴击、防御、伤害构成、命中反馈与附魔管线 |
| 体力 | 基础20，加现有工艺 `skillStaminaCostDelta`，再乘近战配装／临时耗体系数；替代本次普攻成本，只扣一次；不足不触发，已就绪的点击不降格为普通攻击 |
| 起手 | 就绪后左键经过0.25秒持剑转下劈前摇，再进入原接触段；无技能附加前冲／回弹 |
| 扇区 | 正前方总夹角60°（左右各30°），在动画接触窗内持续查询，每目标一次；保持人物身体高度的判定范围，墙体遮挡仍生效 |
| 半径 | `(当前UE兵器基础有效范围+(6+6×等级+55)×1.5cm)×配装范围系数`；保留当前兵器范围标准，技能额外距离仅换算一次 |
| 击退 | `当前兵器击退+(188+6×等级)×1.5cm`，基础版不附加眩晕 |
| 修炼 | 命中人数×1，多目标至少2人额外3，每次直接击杀×15；可叠加，挥空0；不计尸体、召唤物、NoSkillTraining或后续DOT击杀 |
| 存档 | 技能进度版本15，旧档 `FindOrAdd(dashAttack)` 自动加入Lv1并保留原进度；沿用统一保存事务、升级通知；F6技能目录可调整该技能等级 |
| 取消 | 死亡、换装、菜单/动作不可用沿用现有取消入口；已消耗体力不返还，已发生命中结算修炼；释放移动锁并重置准备 |

只有左键出招属于技能：未就绪时保留普通轻／重攻击；已就绪但体力不足不启动任何攻击。完整收势前不接受新出招、移动、视角转动、闪避或跳跃。不会借用大旋风整屏后处理。

## 已有动画接入

直接复用 `SourceAssets/RuneSwordPickaxeOverhead20260920/ImpactV2` 对应的已完成动画：

- 标准握姿 `/Game/Weapons/AzureRunesword20260913/A_RuneSword_Overhead`
- 长握柄 `/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_Overhead`
- 原有 `RuneSwordOverheadFeel`、纵向裂隙、下劈挥击／命中音效继续使用。

源动画仍为2.60秒：0–0.60秒抬手；0.60–1.11秒蓄势；1.11–1.31秒下劈；1.31–1.39秒打击姿态；随后收势到2.60秒。最新V5从源时间0.97秒开始，经过0.25秒前摇，于1.22秒进入60°扇区判定，再按1倍速播放至2.60秒，整次动作约1.63秒。高位冲刺使用两种握柄各自的 `TacticalSprint20260921/A_RuneSword_SprintOverhead`：0.97–1.22秒从持剑姿态过渡，随后保留原下劈、落点与收势。挥砍音效、纵向裂隙和判定在接触窗触发，镜头在前摇内渐入。没有附加前冲／回弹或旧2D的额外冻结／恢复计时。后文瞬发构建记录为历史版本。

## 文件

- 技能：`Skills/DashAttackTypes.h`、`Skills/ColdSteelDashAttackModel.cpp`；定义／注册／存档／升级通知接入现有 ColdSteelSkill 系列。
- 动作：`Weapons/RuneSwordDashAttack.cpp`；`RuneSwordComponent`共用接触反馈；`RuneSwordHitQuery`增加扇区查询。
- 输入与移动：`FPSGAMECharacter` 将原旋风专用移动锁命名推广为近战技能锁，旋风行为不变；冲刺攻击不再驱动角色前移或回弹。
- 界面：`ColdSteelSkillPage`被动卡／详情，`ColdSteelStaminaHUD`小型就绪提示，`ColdSteelDevelopmentTools`技能目录。规划见 `Docs/UI/dash-attack-plan-20260920.md`。
- 数据：`Content/ColdSteelData/skills.json:dashAttack`；图标 `Content/ColdSteelData/Skills/dash_attack.png` 直接复制自用户原项目 `assets/skills/冲刺攻击.png`，未引入第三方下载或新生成图。

## 构建记录与测试边界

22:56 发起 `Tools/Build/Build-Editor.ps1`，当时编辑器未运行。日志：`Saved/BuildEditor/build-20260920-225636.log`。

首次 UHT 阻塞：`Source/FPSGAME/Monsters/WitchMotionCandidate.h(23)` 中 `AssignFoundationSkeleton` 的函数参数 `Mesh` 与继承的 `ACharacter::Mesh` 同名。未修改该其他模块文件；随后读取时该参数已更新为 `TargetMesh`，继续必要构建。

22:59:25 构建指出本轮 HUD 局部变量 `Slot` 遮蔽 `UWidget::Slot`，已改为 `DashCanvasSlot`。22:59:43 再次常规构建结果 `Succeeded`，生成 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。最终日志：`Saved/BuildEditor/build-20260920-225943.log`。

本次是正常基础 DLL 构建，不依赖 Live Coding 补丁；用户下次打开项目即可加载。未主动启动编辑器、PIE、截图、渲染或运行回归；实际操作、视觉、命中与存档由用户测试。未提交或推送工作区。


## 用户反馈修订：原起手、前方60°

以下为9月20日修订记录；抬手／蓄势的保留方案已被9月21日瞬发修订替代。

- 删除 `AdvanceDashAttack` 的位移／回弹执行，攻击Tick回归已有下劈路径；动画资产与原有抬手、下劈、收势时序不改。
- `DashAttackStats`固定输出前方60°，即时覆盖编辑器内可能缓存的旧120°定义；JSON及原生默认角度同步60°。伤害、有效半径、体力与修炼保持原接入数值。
- 移除技能详情中的突进距离行、前冲与回弹说明，改为下劈／前方60°；图标与被动触发方式保持。
- 已打开编辑器对象的原生字段布局保持，旧位移参数槽位置零，不再用于动作；无需修改带资产引用的USTRUCT。
- 构建：通过现有MCP桥提交Live Coding，返回 `CompileNotStarted / Live coding canceled`。对应UBT原因是 `LiveCodingLimitError`：本次需要120个构建动作，超过会话允许的100个；未生成或加载本次补丁。桥接工具没有单次构建上限参数，保留现有编辑器，不更改全局工具配置或强制关闭。需关闭UE后执行 `Tools/Build/Build-Editor.ps1` 常规构建，再打开项目。回执：`SourceAssets/DashAttack20260920/compile-no-lunge-60-degrees.txt`。没有启动PIE或自动测试。

## 2026-09-21：瞬发下劈

- 用户反馈前摇过长，要求恢复直接出手。`TryBeginDashAttack` 在成功启动后令 `Elapsed=ContactStart` 并立即采样该姿态，跳过源动画前1.22秒。首个攻击Tick进行命中判定及挥击音效／裂隙启动；原1.22–1.40秒接触窗对应出手后0–0.18秒。
- 源动画不覆盖，剩余约1.38秒按原速播放，保留打击姿态停顿和收势。奔跑就绪条件、体力、伤害、60°扇区、去重、击退及修炼保持原规则。保留之前群怪查询优化。
- 技能详情和JSON说明同步为“就绪后按左键立即下劈，无抬手蓄势”。
- 必要构建：常规构建因FPSGAME编辑器已打开而停止，没有关闭进程。首次桥接Live Coding返回 `NoChanges`，但基础DLL早于本次源码；不能记为已接入。更新本次两个CPP的构建时间戳后再次提交，UBT确实编译 `ColdSteelSkillPage.cpp`、`RuneSwordDashAttack.cpp`，结果 `Succeeded`，耗时27.29秒；记录保存在 `SourceAssets/DashAttack20260921/compile-instant-ubt.txt`。
- 第二次桥接请求在等待Live Coding结果时超时。读取此次输出时，没有新的FPSGAME补丁产物或应用成功记录，基础DLL仍为00:12:19；因此本轮仅能确认源码编译完成，不能确认当前编辑器已生效。保留现有现场，未重放结果不明的编译请求。还需关闭使用该模块的编辑器后常规构建，再打开项目。未运行游戏或追加测试，由用户测试。

### 常规构建完成 · 2026-09-21 00:28

用户关闭编辑器，并明确同意结束残留进程后继续。仅结束已确认的FPSGAME残留进程PID 31536；进程退出后运行 `Tools/Build/Build-Editor.ps1`，常规 `FPSGAMEEditor Win64 Development` 构建成功，完成基础 `UnrealEditor-FPSGAME.dll` 链接及目标元数据写入，耗时2.58秒。本次瞬发下劈修改已进入正式基础模块，不再依赖前述未完成的Live Coding补丁。日志：`Saved/BuildEditor/build-20260921-002823.log`。未主动打开编辑器、启动游戏或运行测试；用户下次打开项目加载该模块，实际手感由用户测试。
