# 疾律弓弦五段环提示 V2

> 历史方案；当前实现以 [cadence-rhythm-v4-tuning-20261028.md](cadence-rhythm-v4-tuning-20261028.md) 与发布清单为准。退役实物文件的恢复位置见 `Docs/Publication/HighlandBow20261028/archive-manifest.json`。

## 范围与布局

按用户参考图将原横向疾律纹样改为金属角饰、银蓝编织弦环、中央箭纹、五段叠层圆环、右下层数章。准星下复用 `ColdSteelBowResonance` 入口，徽章 60×60 px，顶端位于拉弓条下方 4 px（中心下 68 px），保留经验提示的 136 px 起点。尺寸沿现有 HUD DPI 换算与矮窗约束。无面板、滚动或新增交互，不占用准星中心。

Buff 栏复用同一个绘制器，保留原卡片层数和持续时间。数字沿用 `ColdSteelUI::NumberFont`，金色沿用 HUDGold 系列；蓝色是用户指定的未满层语义色。弦环由缓存的平滑曲线及交编线构成，边线使用软边三角形，单批次提交图形，不加载新纹理或材质，不新增 SceneCapture。

## 数据与状态

- 层数读取 `UBowCadenceComponent` 的服务端复制状态，0–5 层；显示不累加层数、不修改战斗属性。
- 0 层显示暗环；1–4 层按层点亮蓝色圆环，新增一段以 0.38 秒缓动展开；5 层转金色，显示五枚底部光点、呼吸辉光。
- 每次成功节拍刷新时播放短脉冲，包含已经满层继续触发的情况。
- 切换弓弦、换武器、死亡与过期仍使用原有清空规则。取消拉弓不刷新持续时间；不引入命中要求。
- 山鸣弓弦的阿尔卑斯剪影仍走原材质，不受本次绘制器替换影响。

## 数值

律动 Buff 每层拉弓速度+20%，最多5层，满层+100%，持续4秒。疾律弓弦常驻拉弓速度+20%保留，按原属性求和公式计算；原节拍下一次拉弓加成仍按原规则计算。满层腰射扩散−50%、物理伤害+20%保留。+100%表示速度加成，不表示耗时减少100%。

运行时浮窗直接读取 `SpeedBonus()`，同步目录、状态说明与作者生成脚本。现有审查代码的期望值改为读取同一倍率常量，未运行审查或测试。

## 制作与交付

源码：`ColdSteelCadenceBadge`、`ColdSteelBowResonance`、`StatusEffectIconPainter`、`BowCadenceComponent`、`CadenceString`、`StatusEffectsComponent`。撤下疾律旧 HUD MID 的运行时加载；保留历史资产与作者源。新增图形直接由 Slate 绘制，无待导入资产。

必要构建使用 `SourceAssets/WoodSteelLongbow20261026/CadenceBadgeV2_20261028/build.ps1`，沿用项目构建互斥。构建回执落在同目录；未启动编辑器、未进行游戏、视觉或联机测试，由用户测试。
