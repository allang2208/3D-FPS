# 经验到账提示 · 2026-10-17

用户要求：击杀目标或获得角色经验后，在屏幕中心、准星下方显示获得反馈，例如「+200 经验」，沿用当前冷钢金色与字体规则。

## 目标与交付阶段

- 名称与入口：HUD 经验到账飘字 `UColdSteelExperienceFeed`，无按键入口，由真实角色经验增量触发。
- 解决的操作需求：击杀结算后玩家能立即确认本次角色经验到账，不必低头看底部经验条。
- 范围：只增加 HUD 只读反馈。不改经验公式、等级门槛、击杀归属、灵魂、掉落、存档、联机事务和输入。
- 阶段：游戏接入。默认不启动游戏、测试、截图或验收；必要源码构建按后台规则执行，实际画面与手感由用户测试。
- 对照：`ColdSteelAcquisitionFeed`（透明文字动态栏）、`ColdSteelProgressNotification`（升级 FIFO）、`ColdSteelSoulCounter`（金色飘字）、`Docs/UI/ui-cold-steel-design-system.md`、`Source/FPSGAME/UI/ColdSteelUIStyle.h`。

## 信息结构与布局

| 栏目 | 内容与优先级 | 宽屏位置 | 窄窗／矮窗位置 | 固定或滚动 | 显示条件 |
| --- | --- | --- | --- | --- | --- |
| 经验飘字 | `+N 经验`，唯一主信息 | 屏幕水平中心，首条文字顶部在准星下方 96px（1080p 基准） | 同一锚点按 PixelScale 反算，不缩字号 | 不滚动，最多 3 行 | 有真实经验增量且未被面板抑制 |

- 单行横排，不换行、不逐字竖排；数量增长时整行保持居中。
- **每条经验独立套一个贴合文字的直角金框**：透明底、约 1.5px `HUDGold` 细线，左右约 4px、上下约 3px 内边距，并叠加一像素深色描边；框随各自行的堆叠、上浮和淡出移动，不再使用整组大正方形框。
- 新条目最靠近准星，旧条目按 38px 行距向下让位；超过 3 条时等待空位，不静默丢弃。
- 不画玻璃卡、不占焦点、不拦截鼠标；只使用文字、投影和金色描边，避免遮挡准星下方视野。
- 面板打开、鼠标模式、弹药／魔法轮盘、商店／工作台／仓库／冶炼／锻造／开发抽屉占用界面时隐藏并暂停消费队列。

## 主题与资源

| 元素 | 复用主题／组件 | 字体角色与字号档 | 资源来源及加载位置 |
| --- | --- | --- | --- |
| 数量 | `ColdSteelUI::HUDGoldLight` | JetBrains Mono 24px Medium | 工程字体 `Content/UI/GunsmithWorkbench/Fonts/` |
| 单位「经验」 | `ColdSteelUI::HUDGold` | Noto Sans SC 16px Medium | 同上 |
| 投影 | 纯黑，约 0.8 透明度，1.5px 偏移 | 不适用 | 绘制时生成 |
| 每条经验金框 | `ColdSteelUI::HUDGold`，约 1.5px 细线，无填充 | 不适用 | 每条经验独立绘制；宽度=数字+单位+左右 4px，高度=字高+上下 3px |
| 外壳／图标 | 不使用 | 不适用 | 不新增资源 |

字号按 `Pixels × 0.75 / PixelScale` 换算；DPI 变化时重建字体与缓存的文字宽度。

## 数据与动作

| 字段或操作 | 模型／业务入口 | 来源范围与过滤 | 单位／排序／公式 | 更新触发 | 确认、扣除与保存 |
| --- | --- | --- | --- | --- | --- |
| 本次角色经验增量 | `UColdSteelStatusModel::StageTraining` | 真实档案 `Level`／`Experience` 前后差；升级扣除的门槛逐级补回 | 整数经验；`阈值(L)=(20+20L+12L²)×8` | 击杀、魔法批量击杀、通用经验提交 | 只读；不新增存档字段 |
| 通用经验入口 | `UColdSteelStatusModel::GainExperience` | 祭品倍率后的实际到账值 | 整数经验 | 现有 API 提交成功 | 只读 |
| 待显示队列 | `QueueExperienceNotice`／`TakeExperienceNotice` | 最多 16 条，溢出合并到最后一条 | 先进先出，界面一次取走并求和 | 模型事务成功后 | 临时内存，读档／HUD 销毁清空 |

- 同一帧的多段击杀经验合并为一条，避免霰弹或多目标法术刷屏。
- 多级连升显示本次实际获得的全部经验，不显示升级后余额。
- 失败、回滚、读档迁移、开发面板直接改等级不产生飘字。

## 状态与输入

| 状态／触发 | 显示、隐藏或禁用 | 原因文案／反馈 | 选择、焦点、滚动与确认行为 |
| --- | --- | --- | --- |
| 无经验增量 | 完全隐藏 | 无 | 不占输入 |
| 新经验到账 | 淡入并向上漂浮 | `+N 经验` | 不抢焦点 |
| 连续到账 | 最多 3 行，旧行下移 | 同一帧合并 | 只读 |
| 面板打开／鼠标模式／弹药或魔法轮盘 | 隐藏并冻结 | 无 | 关闭后继续；不抢镜 |
| 游戏暂停 | 保持当前帧 | 无 | 不推进年龄、动画和队列 |
| 读档／HUD 销毁 | 清空队列与动画行 | 无 | 不把旧收益带到新场景 |

- 键鼠入口：无；不接管鼠标、键盘、焦点或滚动。
- Construct 只绑定 GameInstance 状态模型；Destruct 清空队列与动画行、释放模型引用；Tick 只更新最多 3 行的年龄、位置与取队列，不扫描档案、不解析 JSON、不加载图片。

## 文件范围与交付

- 新增：`Source/FPSGAME/UI/ColdSteelExperienceFeed.h/.cpp`、`Source/FPSGAME/UI/ColdSteelExperienceNotices.cpp`。
- 修改：`ColdSteelHUDWidget.h/.cpp`（创建与让位）、`ColdSteelStatusModel.h`（队列接口）、`ColdSteelProfileRuntime.cpp`（经验增量捕获与读档清空）、`Docs/UI/ui-cold-steel-design-system.md`（正式规则条款）、`Docs/UI/README.md`（索引）、`skills/ue5-ui-umg-slate/references/fpsgame-panels.md`（复用经验）。
- 复用资源：共享金色、Noto Sans SC／JetBrains Mono、PixelScale；无新增贴图、音频或存档字段。
- 确认退役：无。
- 2026-10-17 运行时修复：方框闭合点的 `Points.Add(Points[0])` 把同一 `TArray` 的元素引用传给 `Add`，触发 container-alias 断言（`Array.h:2196`，5/4/16B 与 `TArray<FVector2D>` 吻合）；改为先复制首点到局部 `FirstPoint` 再 Add。修复已重新编译并重链 Editor 与 Game。
- 必要构建：方形框版本已通过后台 `FPSGAME Win64 Development` 构建，终态 `Result: Succeeded`（187.75 秒），随后在编辑器与命令机关闭后完成 `FPSGAMEEditor Win64 Development` 构建，`Result: Succeeded`（27.33 秒），日志 `Saved/BuildEditor/experience-frame-20261017-game.log`、`Saved/BuildEditor/experience-frame-20261017-editor.log`；Editor DLL 已于 21:20 重链。
- 崩溃修复构建：`ColdSteelExperienceFeed.cpp` 重新编译；`UnrealEditor-FPSGAME.dll` 22:48:37、`FPSGAME.exe` 22:47:43，日志 `Saved/BuildEditor/experience-feed-crashfix-20261017-editor.log`、`...-game.log`，均 `Result: Succeeded`。
- 贴合每条经验金框版本：`UnrealEditor-FPSGAME.dll` 23:05:45、`FPSGAME.exe` 23:06，日志 `Saved/BuildEditor/experience-feed-tightframes-20261017-editor.log`、`...-game.log`，均 `Result: Succeeded`。
- 上一版文字提示的 Editor 构建日志保留在 `Saved/BuildEditor/experience-feed-20261017-editor.log`。
- 预览／检查／测试：用户未要求，未执行；未启动游戏、PIE、截图或验收，实际画面与手感由用户测试。
