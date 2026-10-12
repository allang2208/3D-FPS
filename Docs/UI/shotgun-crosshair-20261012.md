# 散弹枪四段圆环准星

当前散弹枪 SUPER90 的腰射准星由四条直线改为四段等长圆弧。每段 80°，上下左右各保留 10° 缺口；圆心留空，不增加中心点。白色细线叠加暗色描边，以适应明亮和深色背景。

沿用 `GetCrosshairHalfExtent` 的扩散投影，圆弧内沿对齐现有扩散距离，随移动与开火反馈变化。ADS、背包、弹药轮盘及翻越时的显示规则沿用原逻辑；命中反馈继续独立绘制。没有调整武器扩散数值或弹道。

在现有 `UColdSteelHUDWidget::NativePaint` 的 Slate 绘制分支实现，无新增控件、输入焦点或计时器。单位圆弧采样只初始化一次，每帧复用同一组采样与一个有界点数组，不加载资源、不解析目录。

视觉方向参考用户提出的《战地 1》圆形准星。动态反馈理念参考 [EA《战地 1》PC 手册的 Reticle 说明](https://eaassets-a.akamaihd.net/eahelp/manuals/battlefield-1-pc-en.PDF)；四段弧线和间隔为本项目实现，并非提取原游戏素材。

本轮进行源码修改和必要构建，未主动启动编辑器、游戏、截图或进行视觉验收。开发期间用户已有编辑器会话；常规构建被 DLL 占用阻挡后曾使用 `LiveCoding.CompileSync`，补丁阶段报告 `Cannot find image section .voltbl`，编辑器随后崩溃退出。该次不能算接入成功，后续改为常规 Editor 构建，不自动重开编辑器。

`Saved/BuildEditor/build-20261012-201522.log` 中准星文件已编译完成，该轮整体构建因地牢模块的并行修改失败。地牢模块随后已更新。后续随三弹种接入完成了常规 Editor 构建：`Saved/BuildEditor/build-20261012-204018.log`，`Result: Succeeded`，正式 DLL 已更新。没有再次使用 Live Coding，也没有自动重开编辑器；游戏内视觉效果仍由用户测试。
