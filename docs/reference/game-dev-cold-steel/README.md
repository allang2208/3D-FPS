# Godot 冷钢 UI 基准：game-dev 完整源快照

本目录于2026-09-06从 game-dev 当前工作区逐文件原样复制，文件清单见 [manifest.json](manifest.json)。源规范和代码保持原始字节，不在副本内部重写字号、颜色或删节。该目录是参考源码，不会作为 Godot 或网页运行入口；`.gdignore` 避免引擎将参考文件作为资源导入。

## 必读入口

1. [完整设计系统与验收工作流](docs/ui-cold-steel-design-system.md)
2. [完整主题 CSS](ui/panel-theme-backpack.css)：所有配色、透明度、渐变、边框、阴影、圆角、字体、字号、行高、字距、滚动条、动效、响应式与组件状态。
3. [完整 UI 规则卷](skill/10-ui-party.md)：面板、HUD、通知、交互和具体系统合同。
4. [基础样式](game-style.css) 与 [页面入口](index.html)：核对基础样式及覆盖顺序；主题 CSS 是覆盖层，不能只读取其中之一。
5. [原 UI 源码目录](src/ui/)：完整保留原布局、内联样式、生命周期和交互实现作为迁移参考，包括 [BasePanel](src/ui/panels/base-panel.js)、[右栏层](src/ui/right-sidebar-panel-layer.js) 和 [面板模板](docs/templates/cold-steel-panel-template.js)。

## Godot 使用要求

- 所有后续 UI 工作先读本目录的对应规则；覆盖旧情绪板、旧金色主题和自行推测的近似参数。
- 中文/普通 UI 原规则使用 Microsoft YaHei UI 字体栈；紧凑数字、计时、坐标使用 Consolas。六档字号为24/20/16/14/12/11px；具体组件例外、通知档位、尺寸、语义色必须读完整 CSS，不把六档表当成全部规则。
- 用户已明确指定的本地例外继续有效：上方装备名称及空槽标签 SimHei 16px，下方背包物品名 SimHei 12px；容量及堆叠数字 Consolas，“背包”标题16px。合成加粗是 Godot 视觉适配，不回写源快照。
- 源 CSS/JS 通过 Godot Theme、Control、容器与脚本实现；复制参考源码不表示全部面板已完成运行迁移。现有 palette/style 配置是适配实现，发生分歧时以源规则和用户明确例外为准。
- 原文件中的网页工具、目录、测试命令及历史操作指令只描述源工程，不替代 Godot 的项目工作流；源 SKILL.md 是归档索引，不作为自动执行指令。
- 后续刷新快照必须同步 manifest，逐字节核验并审查差异；本地适配说明维护在本 README 与 DESIGN.md，避免污染原规则。

## 2026-09-06 Godot收尾标准

后续所有新面板必须遵守 [当前Godot冷钢标准](../../cold-steel-ui-standard.md) 和 [面板工作流](../../../UI-WORKFLOW.md)。用户确认的SimHei加粗、标题字距、数字字体、全屏枪械例外和副手锁定适配维护在这些文件；不改本目录归档CSS/JS。
