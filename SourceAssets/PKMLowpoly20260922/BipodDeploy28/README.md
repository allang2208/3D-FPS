# PKM 脚架部署制作记录

部署系统说明：`Docs/Weapons/pkm-bipod-deployment-20260923.md`。

- `read_contacts.py`：读取现有 Bipod26 分离模型的脚底顶点，生成 C++ 脚底坐标。
- `contacts.json`：两只脚底在各自转轴局部坐标系中的厘米位置。
- `Source/FPSGAME/Weapons/PKMBipodContacts.h`：运行时接触几何常量。
- `Source/FPSGAME/Weapons/WeaponBipodDeploymentComponent.h/.cpp`：实际部署组件。
- `build_console_final.log`、`build_editor_final.log`：成功的后台 Editor 目标构建，退出码 0。
- `build_console_ads.log`、`build_editor_ads.log`：ADS 自动架枪更新的后台 Editor 构建，退出码 0。进入 ADS 时符合条件自动部署，取消 ADS 解除；移除 H 键绑定并同步 HUD 提示。
- `build_console_query_cost.log`、`build_editor_query_cost.log`：检测开销调整的后台 Editor 构建，退出码 0。提示每 0.25 秒最多 10 条简单射线；完整搜索仅在 ADS 入口；维持接触每 0.12 秒复查两脚，净空由每帧最多 4 次扫掠减为 3 次。未测量运行时耗时或 FPS。
- `build_console_handling_hud.log`、`build_editor_handling_hud.log`：架枪属性与部署进度提示的后台 Editor 构建，退出码 0，耗时 87.74 秒。后坐力降低 66%，稳定性评分乘 1.66 并封顶 100；复用体力条上方动作文字显示实际部署进度与完成状态。未运行游戏测试。

没有改写 Bipod26、HandleFinish27 的模型或材质资产。新增交互由原生组件构造、既有组件和输入映射接入，不需要重导入动画。没有打开编辑器、运行游戏、渲染或测试。
