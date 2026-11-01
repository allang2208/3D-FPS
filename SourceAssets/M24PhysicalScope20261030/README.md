# M24 实体镜片与相对灵敏度

本次仅处理 M24 原装双瞄具 `m24_custom_scope_6x`。不改枪械／手臂坐标、模型几何、机械接口、动作及伤害。

## 灵敏度

采用屏幕中心附近的移动量匹配（focal-length / 0% monitor matching）。不是把高倍镜设成与腰射相同的 cm/360；相同角速度在 6 倍镜中会表现为约 6 倍的屏幕速度。

`gain = tan(current main-camera vertical FOV / 2) / tan(hip vertical FOV / 2) × ADS preference / effective lens magnification`

`effective lens magnification = lerp(1, displayed magnification, scope presentation alpha)`。材质捕获和鼠标读取同一个有效倍率。保留已有滚轮指数过渡和 ADSMouseSensitivity 偏好；不对鼠标加平滑或加速度。1 倍辅助镜恢复正常 ADS 灵敏度，退出 ADS 恢复腰射灵敏度。其余枪械的灵敏度算法不变。

参考主流游戏的设计目标，不照搬它们的滑杆数值：

- [Ubisoft Siege ADS sensitivity guide](https://www.ubisoft.com/en-us/game/rainbow-six/siege/news-updates/3IMlDGlaRFgdvQNq3BOSFv/guide-to-ads-sensitivity-in-y5s3)：区分角度匹配和 visuomotor gain。
- [Call of Duty PC controls/settings](https://www.callofduty.com/blog/2020/11/Black-Ops-Cold-War-Controls-and-Settings-PC)：Relative 与 Monitor Distance Coefficient。

## 实体光学接入

- M24 不再由 ScopePresentation 隐藏持枪者视模；不再绘制 Slate 圆盘、圆框、镜外遮罩或屏幕分划。
- 复用现有唯一 SceneCapture，将 HDR 画面仅绑定到持枪者瞄准镜组件的 `M24_ScopeGlass` 动态材质。原始静态网格与世界武器的材质没有被修改。
- 材质通过网格局部 Y 区分原目镜与物镜，后者仍是镀膜玻璃；上方 1 倍镜保持原材质与红点。
- 目镜实际几何负责裁切。ScreenPosition 采样和相机射击方向共用视野中心，避免晃动时模型 UV 带走分划、造成准星与射线偏离。
- 根据目镜投影大小裁剪捕获视锥；倍率与镜片在屏幕上的大小解耦。没有扩大镜片、挪枪或移动相机。
- 采用线性 HDR 捕获，经主视图统一曝光和色调映射，避免将旧 LDR 界面纹理贴到模型后重复色调映射。
- 十字、0.5/1/5 mrad 刻度按实际捕获角度计算；5/10/15/20 数字为角度读数。细半密位随像素间距淡出，避免远端聚成一团。
- 退出 ADS、换成上方镜、打开菜单、换武器或切第三人称时停止捕获并还原原镜片；只恢复本功能仍持有的材质覆盖。
- 捕获分辨率继续使用 `fps.M24.ScopeResolution`，默认 1024，范围 512–1536；只有主镜 ADS 活跃时捕获，目标与材质在同次装备期间复用。

## 制作和落盘

`author_labels.py` 生成角度数字贴图；`run_assets.ps1` 经现有批次互斥使用现有编辑器或后台 commandlet 创建并保存材质；`build_editor.ps1` 执行正式 UBT 构建，存在编辑器时不会强制关闭。正式保存和构建以各自 receipt 为准。

遵循用户规则：未运行游戏、截图或自动验收。编译／资产落盘不代表运行画面和手感已经验收，由用户试玩。
