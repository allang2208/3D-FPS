# 共振前握把：自然腕肘支撑姿态

本版保留 Compact75 的 75% 前握把模型、三指穿孔姿态及手掌接触方向，只修改左肩带、上臂、肘与前臂的支撑关系。待机腕部轴线折角由约 35.14 度降至 14.13 度；不是把手指重新扭到接触位置。

肩带采用前送、略下沉的支撑站姿，再用双骨链求解肘部，使前臂更接近手掌的自然延伸方向。作者参数 `support_offset=(-.015,.13,-.025)` 相对原动画源设置，并替代 Compact75 中原有的自动伸手补偿；它不是相对上一版再额外前移 13 cm。上臂与前臂长度、手指局部位移、缩放、右手和机械时序保留。肩带偏移仅在前握把支撑阶段启用，沿原权重渐变退出，保留取弹和插匣的原接触段。

`build_animation.py` 使用随附 `fit_final.json` 和 `release_profile.json`；模型与手指拟合参数来自 Compact75，不重新拟合。`validate_arm.py` 对比上一版的手腕、全部左手手指位置和腕肘轴角；`validate_source.py` 检查原动作合同；`check_geometry.py -- --full` 检查手指/握把表面采样。`import_assets.py` 只导入动画，继续复用 `/Game/Weapons/M4AngledForegripCompact75/SM_M4_AngledForegrip`。


## 当前接入与验证

当前动画目录 `/Game/Weapons/M4ForegripWristNatural`，九条动作已切换实际引用。`wrist-natural-v1` 新进程加载 2026093121 模块，255 PASS / 0 FAIL。814 个手指/握把表面采样无交叉，九条源动作合同检查通过。相对 Compact75，全部整数帧手腕及手指骨骼位置差最大约 0.0062 mm，保持原握姿接触；上臂、前臂长度和骨骼缩放未改变。待机腕部轴角约 35.14 → 14.13 度，肘部折弯约 26.82 → 51.46 度。角度是本骨架轴线测量值，不是人体医学测量。

可编辑源 `M4_AngledForegrip_Integrated_Editable.blend`，实机视频 `M4_foregrip_gameplay.mp4`（静音，仅视觉检查）。实机背侧近景 `D:/FPS3D/FPSGAME/Saved/ForegripAudit/wrist-natural-v1/wrist_review.png`。源比对、导入压缩与实际运行证据见 `acceptance.json`。原玩家存档未改动；打开的旧 UE 编辑器需重启加载新模块。
