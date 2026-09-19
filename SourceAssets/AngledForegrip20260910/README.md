# 镂空倾斜前握把候选

本目录用于前握把美术建模与材质预览，未修改游戏配件目录或运行引用。

- `three_views.png`：根据用户缩略图生成的侧、正、顶视概念图；不可见面为三维重建。
- `AngledForegrip_M4_Editable.blend`：可编辑框架、倒角、嵌片与装饰紧固件。
- `AngledForegrip_M4.fbx` / `.glb`：导出模型。
- `beauty.png` / `side.png` / `front.png` / `top.png`：真实 Blender 渲染。
- `turntable.mp4`：48 帧转台预览，12 fps。
- `foregrip_raw.glb`：5080 原始输出，838812 面。
- `Foregrip_5080_Cleaned.blend` / `.glb`：体素连续化、减面与 M4 Body 材质处理后的生成参考，26726 面；仍有局部不规则表面，不作为最终硬表面配件。
- `build_refined.py`：可复现的硬表面作者脚本。
- `export_validation.json`：GLB 读回、焊接 UV/法线拆点后的网格完整性检查。
- `material_provenance.json`：使用贴图的原始路径和 SHA-256。

## 材质来源

当前角色代码加载 `/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416`。对应 Blender 源为 `SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend`。

直接复用源文件 `Body.001` 和 `Grip Default.001` 的 BaseColor、Normal、Roughness、Metallic 节点和贴图；新 UV 映射到已检查的无标志表面区域，避免旧枪械图集的部件边缘、文字和旧轮廓污染新模型。装饰凹槽另用深色材质。

原贴图来自本项目既有 M4 资源，继承原资产许可。用户参考图的再分发许可未提供；本目录仅作本机制作交付，没有公开提交原图或商业贴图。

## 5080 记录

`workflow.json` / `request.json` 保留首次任务；背景移除节点触发缺失模型下载，已发出针对该任务的中断请求。
`workflow_retry.json` / `request_retry.json` 使用不依赖模型下载的背景阈值预处理，同机 TRELLIS.2 服务已成功执行。任务 ID 为 `fa654dd2-ec97-4318-acb5-a546ff9725ca`，计算约 40.97 秒，等待队列耗时另外计算。原始输出已下载；成功记录见 `history_retry.json`。

最终硬表面候选按概念轮廓重新布面和制作细节，不能把手工重建网格描述为 AI 原网格自动优化。生成原始网格已以独立文件保留，并放入 Blender 隐藏参考集合 `5080_RAW_REFERENCE`。

建模候选全部对象有 UV；GLB 读回后焊接 UV/法线拆点，非流形边为 0，零面积面为 0。8 张 M4 原贴图已打包进 Blender 源文件。

后续游戏装配与左手动画已完成，见 [GameIntegration/README.md](GameIntegration/README.md)。最终版调整了镂空内沿以适配现有手套，使用独立 UE 资源 `/Game/Weapons/M4AngledForegripFinal`；枪匠“前握把 → 共振二代前握把”可装卸并保存。`final-v2` 新进程回归 320 PASS、0 FAIL；446 个手指／握把接触采样无交叠。可编辑整合源和实际游戏预览均位于 `GameIntegration/`。

## 三视图生成提示

内置 imagegen，以用户图片作视觉参考：保留镂空三角环、短水平连接座、非对称斜握持面、石墨灰倒角框架、圆形紧固件与细颗粒握持面；同一物体的 SIDE / FRONT / TOP 正交视图，浅灰背景，无尺寸标注，无其他物体。
