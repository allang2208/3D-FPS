# 精简弹药栏 · 2026-09-09

最新要求：在 184×76px 版基础上将高度减半，现为 **184×38px**，右侧与底部间距各 20px。

- 左列：武器名 12px、弹药口径 10px，垂直排列；超长名称受控省略。
- 右列：当前弹数 22px 粗体、12px 分隔符、备弹标签 10px 与备弹数 14px；数字保持完整，不使用 k 等缩写。
- 外壳内边距为横向 8px、纵向 4px，圆角 6px。保持真实字号，不通过整体缩放控件压缩高度。
- 移除余量条、容量/状态文字和换弹按键提示；保留原有数字颜色反馈。
- 使用冷钢配色、宋体和 Consolas；复用真实弹药数据。打开背包时隐藏。

实现：Source/FPSGAME/UI/ColdSteelAmmoReadout.h/.cpp；HUD 负责右下锚点和刷新。
本轮原版及旧截图备份：trash/ammo-half-height-20260909；更早版本备份：trash/ammo-readout-compact-20260909。
编译日志：Saved/AmmoReadout20260909/half-height-build.log，Development Editor 构建成功，模块 UnrealEditor-FPSGAME-2026090948.dll。
实景预览：Saved/AmmoReadout20260909/960-live.png。

半高版实机验收：960×540、1280×720、1920×1080，每种分辨率均通过正常、低弹、换弹、空弹匣、耗尽、大备弹、未装备 7 种状态，共 21 项状态检查，全部进程退出码 0。日志：Saved/AmmoReadout20260909/half-height-20260909231134-{960,1280,1920}.log。

实际查看了 960 的正常/999 弹与 99999 备弹图、1280 空弹图、1920 正常图。38px 高度下当前弹数、备弹数、标签及口径没有裁切；半高面板保持右下角留边。测试复用原有 AmmoReadoutAudit，仅覆盖展示，不改正式弹药与存档。
