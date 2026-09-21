# 闪电迁移（2026-09-20）

已按技能与魔法工作流把原 game-dev 的 `lightningStrike` 接入 UE5 本地单人战斗、技能页、修炼、混合快捷栏和存档。使用现有 Dr.Game Free Spline VFX 的电弧系统制作项目副本。代码与资产已制作、导入；本轮不运行 PIE、测试或效果验收，实机表现由用户判断。

## 原项目依据

只读来源：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev`。

- 定义：`data/skills.json:skills.lightningStrike`；目标、连锁和结算：`src/entities/components/lightning-strike-system.js`。
- 视觉：`src/effects/lightning-bolt.js` 的一次生成固定随机折线、蓝紫色电弧、短暂保持与淡出。UE 重建三维样条与现有 Niagara，不声称像素级还原原 2D 效果。
- 状态：`src/entities/components/damageable-entity.js` 的感电与过载；施法时序来自原 GameScene，UE 复用现行左手释放手势的接触回调，没有新增手臂动画资产。
- 音频：原 `assets/sounds/skills/lightning-1.mp3` 与 `lightning-2.mp3` 同时播放，转为 48kHz 单声道 PCM16 WAV 后导入。

## 数值与时点

本轮保持原闪电数值，未把已单独调整过的火球／冰锥平衡参数套到闪电。配置唯一入口为 `Content/ColdSteelData/skills.json:lightningStrike`，`LightningStats` 同时供施法与当前／下级效果展示。

| 项目 | 基线 |
| --- | --- |
| 等级、修炼 | 1–20；每级所需经验 `100 × 当前等级` |
| 伤害 | 向下取整 `20 + 10L + 魔攻 × (1.15 + 0.25L) + 智力 × (1 + 0.25L)`，再走现有装备、魔法暴击和防御路径 |
| 消耗、冷却 | 30 MP、12 秒；有效起手时提交一次 |
| 总目标数 | `1 + floor((L-1)/5)`，即等级 1／6／11／16 时为 1／2／3／4 |
| 每跳衰减 | `0.9^跳数`，主目标为第 0 跳 |
| 眩晕 | `0.75 + 0.02L` 秒，沿用怪物控制免疫 |
| 世界单位 | 原 1 单位 → 1.5 cm；射程 900 cm、瞄准容差 300 cm、传导距离 300 cm |
| 感电 | 每次 +1 层、每次追加 4 秒；每层后续电伤 +3% |
| 过载 | 达 5 层清空；225 cm 范围，伤害 `floor(20 + 1.2魔攻 + 1.2智力)`、眩晕 1.2 秒 |
| 修炼奖励 | 命中 +4、击杀 +10、多目标命中额外 +10、多目标击杀额外 +10；同次连锁汇总提交 |
| 电弧 | 保持 0.5 秒，淡出 0.25 秒，10 段，形状生成后不持续随机摆动 |

法杖的电伤、目标数、射程、传导／过载范围、控制时长、连锁施法、施法速度、暴击和穿透走现有接口；魔杖乘数保留 `wandSpellMultiplier`。原范围联动使用 `magicRangePercent`。过载仅结算一般击杀收益，不递归叠感电或重复算闪电修炼。

## 三维目标与动作

按键时寻找准星射线附近、在前方且可见的敌对活体；无目标、超距或遮挡不会扣资源。临时左手冲突只排队一次，实际起手重新取数与锁定；双持等长期占手直接拒绝。已有动作自然结束，沿用火球的 `TryBeginSpellGesture` 释放层。

有效起手扣蓝并启动冷却，接触帧只复查锁定目标。目标死亡、离开射程或被遮挡时本次失败，已提交的资源与冷却保留；不会突然改打另一人。后续每跳选择上一目标附近最近的可见敌人，单次不重复命中同一目标。死亡、菜单、退出时清理等待、动作与电弧。

原 2D 鼠标半径改为相机射线的三维横向容差，位置距离按 UE 厘米计算。原过载代码以被感电目标的阵营筛选，可能反向伤到施法者；UE 明确以施法者为敌我依据。闪电是锁定连锁，不属于有碰撞部位的弹道投射物，因此使用随机魔法暴击，不伪造要害直击。

## 现有特效资产与制作

- 原系统：`/Game/_SplineVFX/NS/NS_Spline_ElectricLightning`，已有 Currency／MainPower CPU ribbon 与 Detail GPU sprite、闪电印章／SubUV 材质和贴图依赖。
- 专用系统：`/Game/Skills/Lightning/NS_LightningChain`；原包保持原样。
- `AFPSLightningArc` 以样条作为根组件，Niagara 从 attach root actor 找到样条；生成固定折线和准确端点，设置包围盒、宽度、亮度与短促终点灯光。运行期控制保持、淡出和销毁。
- 作者脚本保留原 Self 生命周期，改 Once；移除 ribbon 的逐帧位置抖动，设蓝紫颜色，并由 `ScaleColor` 将 `Initial.Color` 乘以 `User._Brightness`。原 Infinite duration mode 会隐藏 Loop Duration，脚本不写隐藏输入，统一由运行期结束电弧。
- 音频：`/Game/Skills/Lightning/S_LightningCast1`、`S_LightningCast2`。源文件与转换出处在 `SourceAssets/Lightning20260920/audio-provenance.json`。
- 图标：`Content/ColdSteelData/Skills/lightning_cold_steel.png`，银色六边框、石墨底、蓝紫电弧；生成源保存在同一作者目录。`Tools/UI/prepare_cold_steel_skill_icons.py` 已纳入恢复。

现有包的本地存在及系统结构支持本次制作；本轮没有新增外购或下载，未进行游戏画面验收。第三方 VFX 原包、派生 uasset、原项目声音及转换音频保留本机许可边界，不将本地已有素材等同于可公开再分发。

## UI、进度与恢复入口

技能页全部／主动／魔法分类中位于冰锥之后；详情包含伤害、魔攻／智力系数、目标数、衰减、距离、控制、感电与过载。拖入现有混合快捷栏即可绑定；缺蓝、冷却、左手占用提示复用现行槽位。F6 技能调级包含闪电。

档案版本 13 在旧存档中补入闪电等级 1 和冷却字段，保留已有技能、绑定和物品；不保存进行中的施法或敌人临时感电状态。修炼、玩家击杀经验与暴击奖励经过现有状态事务保存。

恢复顺序：

1. 本机恢复已许可的 `_SplineVFX` 原包、作者图标与原项目两份音频。
2. Python 安装 `imageio-ffmpeg` 后运行 `Tools/Skills/prepare_lightning_sources.py` 转码。
3. 常规构建现有 UE 项目（作者脚本使用 `RainAssetEditor` 与 Niagara MCP 工具类型），编辑器启动后通过 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript .../Tools/Skills/build_lightning_assets.py` 制作并保存专用资源。
4. 图标恢复使用 `Tools/UI/prepare_cold_steel_skill_icons.py`。源码、配置和恢复脚本不代替第三方二进制依赖。

实现入口：`Skills/FPSLightningComponent.*`、`FPSLightningArc.*`、`ColdSteelLightningModel.cpp`、`LightningTypes.h`、`LightningDamage.h`；感电接入 `Combat/CombatStatusFormula.*` 与 `CombatFormulaRuntime.cpp`。

本轮完成 Niagara 资源编译保存及 Editor／Game Win64 Development 常规构建；构建记录在 `Saved/LightningMigration/build-editor.log` 和 `build-game.log`，均为 Succeeded。未运行测试、PIE、战斗回归、截图或验收渲染。连锁手感、视觉亮度和各类武器的实机组合留给用户测试。

## 用户反馈后修复：有伤害／声音但看不到电弧

2026-09-20 用户实测反馈看不到电弧，并确认存在伤害或音效。沿源系统输入链和本机生成的 Niagara shader 定位：原 `ScaleColor002 → Scale RGB → VectorFromFloat → User._Brightness` 是主体发光倍率。首轮作者脚本删除了这个模块，Currency／MainPower 的编译输出不再读取 `_Brightness`，因此 Actor 传入的亮度和淡出失效，仅剩低强度基础颜色。

修复在两条 ribbon 上加入明确的 `ScaleColor`，每帧使用初始颜色乘以 `_Brightness`，Alpha 固定 1；Actor 恢复源资产的 50 倍发光并按既有 0.5＋0.25 秒时钟淡出。恢复 `MainPowerSpeed=8`、`_DetailSpeed=0.0013`、`_DetailSpeedOffset=6`，仅关闭空间抖动，保留材质纹理与电火花运动。资源路径、伤害、目标选择、消耗、修炼和存档不改。

已将修复写入恢复脚本和项目专用 Niagara 资产。诊断输出位于 `Saved/LightningMigration`；离线 shader 导出进程完成了文件输出，但因已有编辑器占用 MCP 端口而返回错误退出码，不作为效果验证证据。本轮没有主动运行游戏或截图，修复后的可见性仍由用户实机复测。

修复后的 Editor／Game Win64 Development 常规构建均成功，日志为 `Saved/LightningMigration/visibility-build-editor.log` 与 `visibility-build-game.log`；编辑器已重新打开加载新模块。

## 原版粗细与层次调整（用户否决，已撤回）

用户反馈「还是上一版好一些」，因此本节方案不再是当前效果。恢复渐细调整前的随机宽度、紫色配色与 HSV 变化、10 段固定折线和默认密度 50；保留更早完成的 50 倍发光、淡出与电火花运动修复。下文仅记录已撤回的尝试，不能据此覆盖当前资产。

用户要求靠近主角的闪电较粗。本轮重新读取原 `lightning-bolt.js` 的实际 `_redraw`：外圈半径 30→5、内圈 19→4、内芯 11→2、白芯 5→1；沿电弧长度线性递减，宽度变化在生成时确定，整体形状固定 0.5 秒后淡出 0.25 秒。

UE 保留已有两条 ribbon 和电火花，按第一人称尺度调整为外圈全宽 60→10 cm、亮芯全宽 22→4 cm（主弧 `_Width=8`；后续连锁沿现有倍率缩放）。宽度按生成索引／点数计算，与样条位置顺序一致；替代原包每点 1–8 倍随机宽度，避免中途突然膨胀。这里保留原版端点比例，不把 2D 像素尺寸直接称为 UE 世界尺寸还原。

颜色采用原版 `0x6a4bff` 蓝紫外圈、`0xdcd6ff` 亮色内芯、`0xa98fff` 电火花，先转线性空间再应用既有发光控制；关闭包内额外的色相／3 倍饱和度随机调整。样条使用原版的中点细分与一次 Chaikin 切角，保留精确起止点；每层 48 个采样点覆盖圆顺接头和连续收细。保留上轮修复的发光／淡出控制，未改动伤害、冷却或修炼规则。

本轮仅制作、资产接入与必要构建；不主动运行 PIE、截图或效果验收，实机视觉交由用户测试。

粗细调整的 Niagara 资产已编译保存；Editor／Game Win64 Development 常规构建均成功，日志为 `Saved/LightningMigration/taper-build-editor.log`、`taper-build-game.log`。
