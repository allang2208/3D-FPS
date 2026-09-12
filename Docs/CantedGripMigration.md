# M4 45° 抓握与 AKM 配件迁移，2026-09-11

2026-09-12 更新：本文为历史迁移记录。当前已接受的 M4/AKM 45° 与阻手器抓握采用 [VRE 扩展](../SourceAssets/VREGripExtensions20260912/README.md)，垂直握把采用 [VRE 垂直手型](../SourceAssets/MannyGraspDonor20260912/README.md)。本文原动画保留为制作/验证输入，配件数据迁移结论按原记录，不因更新握姿改变。

本机已完成 M4 45° 侧倾握把的腕肘方向、并指、拇指对握和松手路径修正，并接入 AKM 的 45°、垂直、棱镜和共振四种握把。每个动作族覆盖九条动画，共 45 条。AKM 枪匠补齐两种缺失握把，16 个 M4 配件选项的数值及效果已核验一致；AKM 基础数值、弹药及原换弹时序保持。

切换 M4 / AKM 时会销毁并重建垂直与侧倾握把组件，避免复用另一把枪的网格。新资源分别由 `M4CantedForegrip.cpp`、`M4VerticalForegrip.cpp`、`M4HandstopVisual.cpp`、`M4AngledForegrip.cpp` 与 `AKMAttachmentVisual.h` 选择。

完整作者入口、五套可编辑 Blend、45 个 FBX、实机视频和比较图见 [作者与交付说明](../SourceAssets/CantedGripMigration20260911/README.md)。最终 [验收摘要](../SourceAssets/CantedGripMigration20260911/acceptance.json) 记录：45/45 个动画读回通过，七组独立游戏/UI 回归通过；4159 个手指与握把采样无交叉。原换弹源已有的指间自交未扩展为新的独有时刻，详细范围见报告。新视觉效果仍以用户审阅为准。

本次公开作者工具、验证摘要与针对本机前置版本的集成 patch。共享 AKM/角色模块仍含并行工作，未整体纳入本次提交；不宣称远端已有完整 AKM 运行源码。授权二进制、原始姿态采样与完整资源按 [AssetSetup](AssetSetup.md) 保留本机。当前宿主已实际接入；使用新进程验证，旧编辑器需保存并重启加载新模块。
