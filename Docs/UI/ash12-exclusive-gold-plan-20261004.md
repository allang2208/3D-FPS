# ASH-12 专属改造金卡

用户要求将 ASH 专属改造统一使用现有金色卡片。入口为枪匠面板，沿用 `UM4GunsmithWidget::BuildOption` 的 UMG 宿主与 Slate 卡片。

| 武器 | 槽位 | 改造 ID | 卡片 |
| --- | --- | --- | --- |
| ue_ash12 | muzzle | ash12_tactical_suppressor | ASH 战术消音器 |
| ue_ash12 | muzzle | ash12_tactical_brake | ASH 战术制退器 |
| ue_ash12 | stock | ash12_cheek_rest | ASH-12 贴合式托腮板 |

两款枪口件已在专属身份名单中，本次补齐托腮板。按武器、槽位、改造 ID 精确匹配，使用共享 `ExclusiveCard`、`ExclusiveBorder`、`ExclusiveText` 和悬停／按下主题。

卡片布局、字号、灰阶部件图标、详情、滚动和宽窄屏适配沿用现有枪匠面板。专属文字与已安装／已选待应用状态共存，选择时继续使用绿色反馈。

显示数据仍从枪匠模型读取，构建卡片时确定专属身份；选择、应用、保存、输入焦点和关闭清理由现有控件与业务入口管理。本次无需资源导入、存档迁移或属性修改。

源码入口：`Source/FPSGAME/UI/M4GunsmithLayout.cpp`。源码及文档已落盘。尝试使用已有编辑器编译时，该会话已退出，MCP 连接未建立；随后改为后台常规 Editor 构建。等待已有构建结束后，`FPSGAMEEditor Win64 Development` 返回 `Target is up to date` 和 `Result: Succeeded`，日志为 `Saved/Diagnostics/ASHExclusiveGold20261004/editor-build.log`。未启动编辑器、游戏、预览或测试，由用户测试。
