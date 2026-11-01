# M24 原装 6 倍镜：镜内分划与表面细节

本轮只修改 `m24_custom_scope_6x` 的镜内显示及独立静态镜体的材质绑定。

## 镜内显示

- 单独的细十字线与加粗外侧引导线，替换原来共用的 LPVO 环形分划。
- 主刻度为 1 mrad；半密位刻度为 0.5 mrad，像素间距不足时淡出。四向最多 20 mrad，横向及下方每 5 mrad 标数。
- 刻度坐标为 `focal_length * tan(mrad / 1000)`。焦距来自当前主相机的 `FSceneViewProjectionData`，包含 ADS 过渡、FOV 后坐变化、实际约束视口和 UI 尺度。数字是角度读数，不是弹道距离或自动归零档位。
- 十字中心始终沿用当前相机瞄准点，眼位晃动只影响原有外围镜影；维持固定 6 倍及短边 85% 的圆形视野。
- 不新增场景捕获或渲染目标。减弱原镜边折射、开火全镜泛光和热雾，保留外围开火反光。M24 不再叠加脏点层。
- 分划顶点缓冲由 Widget 持有并复用，仅在原装 M24 高倍 ADS 可见时绘制。

源码：`Source/FPSGAME/UI/M24ScopeDrawing.{h,cpp}`、`LPVOScopeWidget.{h,cpp}` 与 `Weapons/ScopeOpticalPresentation.cpp`。

## 材质制作

- 运行网格仍为 `/Game/Weapons/M24/Surface20261027/SM_M24_m24_custom_scope_6x`；几何、UV、轴、安装位置、动作与瞄线不变。
- 专用 `MI_M24_ScopeSatin` 继续以 `M_M24RegionalSurface_Static` 为父材质，继承 WS1 表面、原刻字保留与单层淋湿逻辑。
- 2K UV0 分区控制图来自原作者模型的 13,726 个镜体三角形，制作值见 `finish_recipe.json`。主体金属粗糙度 .37、旋钮 .32、滚花环 .40、安装座 .43；源 ORM 保持金属／非金属身份，橡胶和内壁分别保持较高粗糙度。
- 保留原 4K 结构法线及既有绿色通道转换。减少细颗粒和大块斑驳，保留接缝、滚花和窄边反射。未改共享母材质或公共预设。
- 新建独立镀膜玻璃母材质与主／副镜片实例；中心透明度分别 .018/.012，掠射透明度 .22，粗糙度 .045，非金属，无额外折射偏移。
- 仅更换此网格的三个材质槽，游戏与使用同一网格的改造预览共同读取。

资产目录：`/Game/Weapons/M24/ScopeDetail20261028`。

## 后台入口与交付状态

`read_source.py` 读取源模型用于制作；`author_finish.py` 生成材质数据纹理；`run_assets.ps1 -Stage install` 定向导入和保存；`build.ps1 -LinkOnlyWhenClosed` 在编辑器关闭后链接。

`install_receipt.json` 和 `build-receipt.json` 分别记录实际保存与构建结果。未启动游戏、未截图、未渲染、未做运行或视觉验收，由用户测试镜内效果。
