# 弓腰射朝向对齐准星（2026-09-26）

用户要求拉弓和箭矢的朝向对准腰射准星。本批调整运行时表现层，沿用已有 V10 动画、版本 19 的右下偏移与视频音效。

## 实现

`BowWeaponComponent::UpdatePoseLayers()` 读取当前帧未经姿态层叠加的握把、真实勾弦标记和箭台位置，以实际箭尾到箭台的轴线求对准旋转。求解目标位于相机中央射线上（距离采用弓的 `RangeCM`），因此瞄准的是腰射准星中心方向，不跟随每次发射的随机偏差。

旋转以握把为支点，握把位置继续使用 `bow_hip_offset_cm = 0,32,-12`。同一个 BowPivot 搬运双手、弓体、弦与箭，不单独扭转箭杆或拖动手指。下蹲侧倾先叠加，再求箭轴对准；满 ADS 继续使用既有对位。

新增一个末尾私有权重 `HipAimProgress`，由原有动作时钟推进：0.2 秒举弓期间进入对准，拉弓／满拉／已搭箭 Ready 保持，放箭随动后平滑退出。取消与切换装备沿用原有生命周期，重新加载表现时清零权重。`AnimatedRiserMount()` 统一几何和朝向计算的挂点变换，避免读取上一帧的世界变换。

没有新增 Tick、场景射线检测、资源加载或配置文件读取；没有改动随机散布、扣箭、伤害、箭的实体弹道和 ADS 精度。

## 交付状态

源码已落盘：`Source/FPSGAME/Weapons/Bow/BowWeaponComponent.h/.cpp`。修改前快照在 `Saved/BowHipAim20260926/Before/`。

后台构建已随 ADS 调整完成，`FPSGAMEEditor Win64 Development` 返回 `Result: Succeeded`。记录：`Saved/BowAudioStillNorth20260926/build-bow-ads-clearance-20260926.log`。后续 ADS 对位调整见 `dark-bow-ads-clearance-20260926.md`。未启动或关闭编辑器，未运行游戏、测试、截图或验收。
