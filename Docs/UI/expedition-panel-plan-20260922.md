# 出征面板重构 · 2026-09-22

## 范围

用户授权：参考原 gamedev 出征准备界面，按 FPSGAME 冷钢 UI 规则开发面板；不迁移其他数据。参考源为旧项目 `src/ui/expedition-system.js` 与 `src/ui/panels/hud-panels-expedition-quest-reward.js`。沿用目的地、情报、队伍准备、行动确认的信息结构，不复制旧目录、解锁、钥匙、奖励、队友或存档。

入口为主场景方形祭坛：靠近、准星瞄准并按 E；Esc 返回。用户纠正后移除 O 快捷键。独立 UUserWidget / Slate 面板通过 PlayerController 管理输入与现有窗口互斥；祭坛沿用 StaticMeshActor 与标签，不新增需要写入地图的原生类。

## 布局与主题

| 区域 | 内容 | 宽屏 | 中屏 | 窄屏 |
| --- | --- | --- | --- | --- |
| 固定标题 | 出征、状态提示、返回 | 顶部 | 顶部 | 顶部 |
| 目的地 | 搜索、全部/可出征、状态列表 | 左栏 | 左栏 | 分页 |
| 任务情报 | 几何门廊装饰、概览/奖励/规则 | 中栏 | 右栏，准备区下接 | 分页 |
| 行前准备 | 当前角色、等级、装备、进入条件 | 右栏 | 右栏下接 | 分页 |
| 固定页脚 | 选中目的地、不可出征原因、确认 | 底部 | 底部 | 底部换行 |

按实际可用宽度 1280 / 900 重排，不整体缩小画布。各主体独立滚动；窄屏三等宽页签切换。标题和行动按钮不随列表滚动。长文字换行，6px 中性滚动条。玻璃外壳使用 ColdSteelUI，工作台玻璃 blur5/radius13；黑灰/银白，状态色仅用于实际条件。中文 Noto Sans SC；数字 JetBrains Mono；20/16/14/12px；按钮36px、间隔4px，圆角10/8/6px。

## 数据与动作

新增纯展示结构 FColdSteelExpeditionDestination；SetDestinations 接收调用方已整理好的信息，不查询或写入出征业务。默认仅提供本 UE 已有地下设施主题的 UI 目录卡，明确“待开放”，推荐等级、奖励、费用没有来源则显示“暂无情报/待公布”。不得把未知值当作0或免费。

角色名称、职业、等级与当前装备只读现有 UColdSteelStatusModel，订阅 OnChanged 刷新并在销毁时解除。无招募、消耗、传送、读写存档。确认通过委托提交选中 ID；没有接收方或状态不可用时禁用，并解释原因。默认目录没有出征接收方，不会进入关卡。

支持空目录、搜索无结果、未知情报、锁定原因、选择失效、关闭重开、窄屏切页。筛选后从可见项选择，清空筛选可恢复目录；刷新保留仍有效的选中 ID。规则采用可读内页，不叠加多层弹窗。

## 接入与交付

新增 UI/ColdSteelExpeditionWidget.h/.cpp、ColdSteelExpeditionLayout.cpp、ColdSteelExpeditionController.cpp；对 PlayerController 和现有打开面板函数做最小互斥改动。关闭恢复此前背包或游戏光标状态，解除本面板自身的输入锁。

必要构建：Editor 原生目标增量构建。用户未要求测试、运行、截图或渲染；不执行这些步骤，由用户测试。

## 使用与后续对接

- 靠近主场景方形祭坛并瞄准，按 E 打开；Esc 或右上返回按钮关闭，Ctrl+F 聚焦搜索。O 不再打开面板。
- 默认显示“地下设施”主题卡；这只是当前 UE 地牢方向的介绍，不声明已经解锁，不绑定关卡跳转。
- 概览、奖励、规则可以切换；“可出征”筛选在默认目录下显示空态，并提供“重置筛选”。
- 窄窗口选择目的地后切到任务情报，顶部三分页仍可返回目录或准备。
- 角色姓名、职业、等级与武器读取当前档案；没有复刻旧角色、钥匙或队友数据。
- `SetDestinations` 替换展示列表，保留仍可见的选中 ID；缺失值显示待公布/暂无情报。
- `OnDepartureRequested` 是未来宿主的确认接口。只有选中项允许出征且已绑定接收方才启用按钮；该接口由调用方负责业务，面板没有扣除、存档或传送代码。
- 面板本身不迁移 Content 业务数据。随后按用户要求，在主场景 `DayNight_Lighting` 放置现有方形祭坛网格；`ColdSteel.ExpeditionAltar` 标签标识出征入口。提示和 E 操作使用同一准星射线（2.5m、遮挡生效），面板打开期间隐藏提示。没有运行测试、截图或渲染。
- 必要构建完成：`Build.bat FPSGAMEEditor Win64 Development -Project=D:\FPS3D\FPSGAME\FPSGAME.uproject -WaitMutex -NoHotReloadFromIDE` 返回 `Result: Succeeded`。这只记录原生构建结果，实机交互和视觉由用户测试。

### 后续祭坛入口接入的构建状态

本页上面的成功构建是面板初版。用户纠正为祭坛入口后，`ColdSteelWorldInteraction`、`ColdSteelCrosshair`、`ColdSteelExpeditionController` 和 `FPSGAMEPlayerController` 的本轮源文件已完成编译，但 Editor 目标在链接时遇到当前工程其他改动的 `AAuthoredDungeonGenerator::EndPlay` 未定义符号（LNK2001/LNK1120）。保留地牢文件原状；祭坛 E 交互的最新源码尚不能据此声明已在运行中生效。未重启或结束其他编辑器，未执行测试。

主场景祭坛已生成于编辑器，最后关卡保存因 `DayNight_Lighting.umap` 被占用而失败（Windows 错误 32）。未保存场景和制作脚本均保留；接入未完成，记录见 `SourceAssets/SquareAltar20260922/hub-placement-pending.md`。
