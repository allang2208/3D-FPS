# 头盔第一人称内壁：镜头同步与压暗

用户反馈头盔内壁固定不动，屏幕抖动时显得僵硬；内壁过亮，缺少封闭头盔的昏暗感。

## 显示与运动来源

沿用 `UFPSHelmetVisorWidget` 的拥有者本地第 15 层：位于瞄具画面上方、正常 HUD/背包下方，保持不可点击；死亡、第三人称或切到其他观察对象时隐藏并重置运动基准，卸装仍由头部装备组件移除 Widget。

当前相机由三层构成：

1. `FPSGAMECharacter::UpdateCamera` 写入走跑、落地、开火和武器/魔法动作的组件位置与旋转。
2. `WeaponActionCameraComponent::Apply` 通过相机 additive offset 叠加换弹触点、装备及冲刺反馈。
3. 身体反应与 PlayerCameraManager 的 CameraShake 继续作用于最终视图。

遮挡层在绘制时读取 PlayerCameraManager 的最终视图，减去控制器瞄准方向，复用实际反馈时钟。位置由相机相对父节点的短时偏移，以及最终视点相对相机组件的附加位移组成；角色世界移动不进入该偏移。相对位置基准缓慢跟随蹲起等姿态变化。

没有新建周期摆动、动画组件、资源加载或独立 Tick。每个世界时刻只推进一次位置基准，重复绘制不重复积分；重新显示或长时间中断时重置。

## 视觉参数

- 水平位移不超过视口宽度的 1.2%，竖直位移不超过高度的 2%，滚转不超过 0.9°。
- 晃动强度由 `fps.Helmet.Motion` 控制，默认 1，范围 0–1。
- 内壁使用线性 RGB 乘色 0.38，由 `fps.Helmet.InteriorBrightness` 控制，范围 0–1。alpha 保持原值，透明眼缝中的场景和 HUD 不受该乘色影响。
- 延展 Clamp 采样的边界像素，为移动和旋转留出屏外余量。几何与 UV 同比例扩展，保留已经拓宽的中央开口尺寸。
- 继续使用当前 `FirstPersonWide20261020` 纹理，无纹理重导入或外部头盔模型改动。

## 源码与交付

修改 `Source/FPSGAME/UI/FPSHelmetVisorWidget.h/.cpp`；构建入口 `Tools/SteelArmet/run_build.ps1` 同时构建 Editor 和 Game。修改前源码保存在 `SourceAssets/SteelArmet20261019/VisorMotion20261020/Before/`。

`visor-motion-build-02` 的 FPSGAMEEditor 与 FPSGAME 均构建成功，基础 DLL 与游戏构建产物已落盘。本次无需重导或另存纹理资产。首轮编译遇到局部变量与 `UUserWidget::Padding` 成员重名，已更名解决。

未启动编辑器或游戏、截图或进行运动/亮度验收，实际幅度与暗度由用户试玩确认。
