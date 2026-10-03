# 左下角生存状态栏 · 2026-10-03

本轮接入饥饿度、缺水度、SAN，默认上限和初始值各为 100。沿用当前冷钢 UI 正式规则及共享 ColdSteelUIStyle。用户已选择 A，正式采用紧凑横排；旧 A/B 图片已按授权归档。离线设计图不是游戏截图。

## 数据与运行规则

UFPSSurvivalComponent 为角色默认组件，服务端权威，0.25 秒更新一次；拥有者接收复制状态。展示只读，沿用 HUD 现有刷新周期，不增加每帧 JSON 解析、控件重建或图标捕获。配置在 Content/ColdSteelData/survival.json，启动时读取一次。

| 项目 | 初始/最大 | 本轮暂定衰减 | 耗尽规则 |
| --- | --- | --- | --- |
| 饥饿度 | 100/100 | 0.05 点/秒，满值约 33 分 20 秒 | 与缺水共用损血计时 |
| 缺水度 | 100/100 | 0.075 点/秒，满值约 22 分 13 秒 | 与饥饿共用损血计时 |
| SAN | 100/100 | 活跃地牢中 0.02 点/秒，满值约 83 分 20 秒 | 归零后食水消耗×2、六维总属性×0.5，恢复到0以上解除 |

饥饿度、缺水度按用户指定口径从满值向零递减；100 代表储备充足、0 代表耗尽。任一归零后，每满 1 秒直接损失当时最大生命的 10%；同时归零仍为 10%，不重复叠加。仅计算到零后的时间，恢复食物/水分使两者都大于零时清除损血计时。生理损血复用当前死亡、蟠桃续命和重生链，不受物防、闪避或月影庇护减免；开发无敌开关仍有效。

SAN 探险判定使用当前世界 UDungeonRunSubsystem::IsRunActive()。普通怪物不默认扣 SAN；实际受到攻击后，读取攻击来源/所属怪物的 Actor Tag 或类名映射，取命中配置中的最大扣减值，再乘 monsterSanityMultiplier。两张映射表目前为空，等后续系数确定。项目没有为任意现有怪物擅自指定 SAN 攻击。

后续接法：monsterSanityLossByTag 的键为怪物 Actor Tag，monsterSanityLossByClass 的键为 UE 类名（例如手工填写的 Blueprint 类名应带 _C）；可在服务器/蓝图中直接调用 ApplySanityDamage(BaseLoss,Coefficient)。食物、水和精神恢复使用 RestoreResources(Food,Water,Sanity)，三者均夹到 0..上限。本轮未新增食物物品、饮水交互或精神药品。

当前值、上限与不足 1 秒的损血时钟追加到 FColdSteelProfile.Survival，沿用既有 A/B 存档与自动保存周期；旧档缺字段自然补满，不清空库存。暂停/死亡/离线不消耗；切图保留数值。2026-10-03 用户调整：死亡重生及蟠桃原地复活的饥饿度、缺水值、SAN 均从 60 点开始；首次新建角色仍为 100 点，默认最大值仍为 100。恢复后的非耗尽状态清除损血时钟。联机后续库存上行保留服务端生存状态，避免旧快照回滚。

## 两版结构与布局

| 项目 | A：紧凑横排 | B：纵向记录 |
| --- | --- | --- |
| 层级 | 等级 + 生命/魔法，下面三个生存指标 | 等级侧签 + 五项纵向资源记录 |
| 常规尺寸 | 最宽 440px，高 184px（已选版优化） | 最宽 440px，高 292px |
| 饥饿/缺水/SAN | 标签 12px、当前值 14px、6px 细条 | 标签 12px、当前/上限 14px、10px 细条 |
| 状态反馈 | 耗尽损血优先，其次低 SAN，再次食水储备低 | 相同的数据与优先级，五项更易逐项阅读 |
| 默认 | 使用此版 | 保留切换入口 |

复用现有 12px 视口边距与中央快捷栏避让；紧凑窗口把左下卡片抬高到快捷栏上方，不整体缩小字体。饥饿度、缺水度、SAN 低于或等于 25% 提示 Warning，归零用 Danger。玻璃 #1A1A1AF8，模糊强度 9、半径 21，外框圆角 10px/1px 银灰线；四角沿用现有金色四分之一圆弧和短切线，淡金亦用于等级身份。中文 Noto Sans SC、数字 JetBrains Mono，沿用 px×0.75/PixelScale 点数转换。生存轨道的克制麦金、水绿与淡紫注册到共享主题，不染色整块背景。

选版后的细节优化参照 ColdSteelHUDNavigation、WorldClock、EventTimeline 和 AmmoReadout：A 高度从 208 压到 184px；生命/魔法与下方三项资源之间加共享 Border 色的 1px 分隔线，生存区上方留 12px，标签与数字保留 6px 最小间隔。金角线已有运行时绘制入口，继续通过 TopVitalsTint 的 GetPaintSpaceGeometry 与实际 CornerRadii 对齐，1.25px 线宽、0.75px 中心内缩、6px 切线；不叠加第二层金线。上一版离线图遗漏这层装饰，已更新作者脚本，历史原始对照图保留。

HUD 不接管鼠标、键盘或焦点，跟随原仓库打开/收回隐藏；UMG 树与资源条的 Slate 引用由原生命周期释放。警示文案随状态变化，不播放新增闪烁或音效。

游戏内控制台切版：`fps.HUD.SurvivalLayout 0` 为 A，`fps.HUD.SurvivalLayout 1` 为 B。

## 文件与交付

- 系统：Source/FPSGAME/Survival/FPSSurvivalTypes.h、FPSSurvivalComponent.h/.cpp。
- 接入：角色默认组件及档案应用、FPSCombatHealthComponent 扣血/怪物 SAN 入口、ColdSteelProfileRuntime 存读、ColdSteelInventoryTypes 追加字段、ColdSteelInventoryRules 数据合法性、ColdSteelPlayerState 的权威字段合并。
- HUD：ColdSteelTopVitals.cpp、ColdSteelHUDWidget.h、ColdSteelResourceMeter.h/.cpp、ColdSteelUIStyle.h。
- 设计图与预览：SourceAssets/SurvivalHUD20261003/；使用工程现有字体，未引入外部素材。
- 必要构建：后台常规 Editor/Game 目标，不启动/重启 UE 或游戏。构建状态另见本轮交付。
- 用户未要求游戏检查、测试或验收；未运行，交由用户测试。

## 本轮构建记录

后台等待已有 UE/UBT 进程结束后，执行常规 FPSGAMEEditor 与 FPSGAME Win64 Development 构建。两目标均返回 `Result: Succeeded`；本轮调用返回 `Target is up to date`、0 action，没有触发重复编译。记录分别为 Saved/BuildSurvival20261003/FPSGAMEEditor-20261003-004243.log、FPSGAME-20261003-004245.log。未启动编辑器、游戏或测试，运行效果由用户测试。

已保存两版同数据对照图 SourceAssets/SurvivalHUD20261003/survival-ui-A-B.png；单版与耗尽状态分别为 survival-ui-A.png、survival-ui-B.png、survival-ui-A-depleted.png、survival-ui-B-depleted.png。作者脚本为 Tools/UI/render_survival_hud_reference.py。全部是离线 UI 设计参考，不是实机截图。

用户选择 A 后的优化已完成常规 Editor/Game 后台增量构建，分别重新编译 ColdSteelTopVitals.cpp 并链接 UnrealEditor-FPSGAME.dll 与 FPSGAME.exe，两目标均 `Result: Succeeded`。日志为 Saved/BuildSurvival20261003/FPSGAMEEditor-20261003-004658.log、FPSGAME-20261003-004712.log。未启动 UE、游戏或测试。

## 等级区域空间修订

用户提供的截图显示等级金框实际横向占了约三分之二的卡片，将生命、魔法的名称与数字挤在右侧。原 USizeBox 的 WidthOverride 只是期望宽度；全宽生存栏跨列参与同一 UGridPanel 的列宽测量，再加上等级槽 Fill 对齐，导致等级实际获得远超 64px 的空间。

此次将等级与生命/魔法放入独立 VitalsCoreGrid，外层只排整宽区块。等级槽左对齐、垂直居中，方块为 64×56px；右侧资源列使用剩余宽度，标签、数值和进度条不再受下方三项指标的列宽影响。A 的总宽高、下方三列、圆角金线、字体和数值规则保持现行规格。此轮只完成后台源码与必要构建，未运行测试或截图。

离线作者脚本已同步为 64×56px 等级方块。本轮未重渲染设计图，目录中已有 PNG 为修订前的历史参考，不作为此次运行效果证明。

上一轮已选版参考图为 SourceAssets/SurvivalHUD20261003/survival-ui-A-refined-reference.png，单卡及耗尽态为 survival-ui-A-selected.png、survival-ui-A-selected-depleted.png；作者脚本使用 `--selected-a`。这些 PNG 与原 A/B 对照图均保留为历史参考。本次等级修订只调整 HUD 布局，复用现有金角线，未改动其他面板、玩法数值或存档字段。

等级修订的后台常规构建已完成：FPSGAMEEditor 返回 `Result: Succeeded` / `Target is up to date`；FPSGAME 实际重新编译 ColdSteelTopVitals.cpp 并链接 FPSGAME.exe，返回 `Result: Succeeded`。日志分别为 Saved/BuildSurvival20261003/FPSGAMEEditor-20261003-005912.log、FPSGAME-20261003-005914.log。未启动编辑器、游戏、截图或测试。

复活资源 60 点修订已完成常规 Editor/Game 后台构建和二进制落盘，死亡重生与蟠桃原地复活均已接入；复用原存档和生存状态字段，无结构变更。日志目录为 Saved/BuildSurvival20261003。本轮未启动 UE、游戏或测试。

## 本轮整理后的当前入口

最新 SAN 归零规则见 [生存与消耗品整理发布](survival-consumables-publication-20261003.md)。上文旧候选 PNG 已移入 `trash/survival-consumables-retired-20261003`，原路径、目标与 SHA-256 在 `SurvivalConsumablesPublication20261003/archive-sources.json`。当前布局继续采用 A 和独立核心 Grid；保留的 refined A 是历史设计参考，最终等级框尺寸以源码／作者脚本为准。
