# 剑的动态预览与背包装备图标

用户授权：参照枪械，将装备加工面板内固定的剑图片接入可调整视角的实时预览，并同步背包、装备栏图标。

- 结构与主题：复用现有装备加工中央场景、冷钢背景、UMG 宿主及 Slate 拖动表面；左右目录和数值、强化与附魔操作保持原入口。剑显示真实模型与材质，支持左键拖动旋转、滚轮缩放、双击／按钮复位；剑不显示枪械的瞄准按钮。
- 数据：读取当前物品的 `world_mesh`，与世界物品显示使用同一个剑资产。工作台和图标共用几何朝向与居中方法；预览只改变展示副本，不修改装备、人物姿势或存档。
- 图标：在现有 `ColdSteelWeaponIcons` 队列中接入剑；背包、装备、仓库及浮窗沿用 Request／Find／OnReady，无单独队列。剑图标使用适配原 2×4 占格的竖向构图，并生成当前目录 PNG 供等待与失败时回退。图标固定构图，不因工作台临时旋转而持续重绘。
- 响应布局与生命周期：使用展示模型包围盒适配当前捕获纵横比，保留预览区域裁切和正文滚动。当前物品刷新保留观察角度，切换物品复位。空／不支持物品回退目录图；关闭释放鼠标捕获、展示组件、渲染目标及短期纹理请求。
- 文件范围：M4StandalonePreview／M4GunsmithPreview 及资源管理、共享预览输入、装备加工预览按钮、武器图标子系统和定向目录图导出入口。必要 Editor 构建和剑目录图资产制作；不运行游戏或验收测试，由用户测试。

实施状态：实时剑模型、拖动／缩放／复位、瞄准按钮按类型显示、共享动态图标和目录 PNG 已完成。`Build-Editor.ps1` 构建 `FPSGAMEEditor Win64 Development` 成功，日志 `Saved/BuildEditor/build-20260914-232326.log`。定向目录图制作命令 `-run=ColdSteelWeaponIconCatalog -Definition=ue_rune_sword -AllowCommandletRendering -RenderOffscreen` 已生成 `Content/ColdSteelData/Icons/ue_rune_sword.png`，输出 384×768 RGBA，退出码 0；制作日志 `Saved/BuildEditor/sword-icon-export-20260914.log`。本次未启动游戏、未运行 UI 交互或视觉验收，由用户测试。
