# 201 大弹鼓改造 — Drum46

**接头外观已由 [DrumJoint47](../DrumJoint47/README.md) 替代。** 用户指出上方漏空和疑似原装弹匣残留；D46 复制的原厂上段包含筋条及不完整表面，不能作为合格接口继续使用。现用网格路径保持不变，模型与图标以 D47 为准，D46 的动作和运行接入保留。不要重新运行此目录完整安装器覆盖 D47 接头。

2026-09-30，按用户要求复用现有认可的大弹鼓换弹，适配 201 的接口与手部接触。当前模型、PBR 材质、十条动画、图标与运行接入已落盘；未运行游戏、PIE 或验收渲染。

## 改造与装配

- 在 201 的弹匣槽增加公共 `large_drum` 选项，属性复制现用 AKM 同 ID 配件：容量 +30 发、换弹 ×1.75、开镜耗时 +10%。201 原厂为 30 发，安装后为 60 发；原厂弹匣与 `lmg201_cloth_box`（125 发）继续可选，三者互斥。
- 鼓壳来源为当前 `/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_drum`，保留已制作的鼓壳、盖、锁扣、紧固件和 UV0。替换 AKM 插入颈，使用当前 201 原厂弹匣上部及内部封面，新增圆角过渡肩；不缩放鼓壳和手模。
- 从当前 201 的 `WPN_root` / `WPN_SOCKET_Magazine` 参考变换提取接口，静态 FBX 直接写在 **201 弹匣骨骼空间**。运行时位置与旋转恒等，仅使用 .01 单位补偿。源参数 `model.json`，实际 UE 网格 `/Game/Weapons/LMG201/Drum46/SM_LMG201_LargeDrum`。
- 插入颈沿用当前 201 弹匣材质与原 UV；新鼓聚合物、金属紧固件、过渡肩使用独立材质，按现用 J44 聚合物粗糙度 .46 与 G43 弹匣涂层 .385 取值，保留鼓自身法线与表面分区。湿润映射追加到 201 配件材质表，不修改原材质。
- 改造二维图标由实际网格制作，灰阶、透明背景、水平侧视。三维预览、实际持枪、掉落鼓使用同一个网格；部件切换沿用现有枪匠应用、取消、物品实例保存及载入入口。

## 换弹来源与局部适配

- 动作母版为当前安装的 `AKMDrumFreeDrop20260920/base/A_AKM_drum_reload[_empty]`（PalmGripV3）：旧鼓自然落下，左掌向上、四指包住鼓壳，托起并装入。历史来源见 [AKM 大弹鼓制作记录](../../AKMDrumFreeDrop20260920/README.md)。
- 普通／空仓分别保持 401 / 516 个 120 Hz 源样本、3.333333 / 4.291667 秒；运行速度仍由公共改造与角色属性缩放。
- 左臂肩、肘、腕、twist/helpers 与手指复制完整原生 FK 链，仅按鼓壳约 1.10 mm 的横向落位差作整链接触平移，依据 201 枪根转换；没有重新设计手型或独立扭转手腕。
- 初始脱手和返回适配当前 201 原厂护木、vertical、canted、prism、angled 五类支撑姿态，共十条普通／空仓动作。战术垂直沿用 vertical。
- 来源 201 `Magazine24` 的右臂、后握把接触修正、枪根、枪机等轨道保留；只覆盖左臂与弹匣骨。布箱当前 `ClothReload44` 动作使用独立字段，避免弹鼓覆盖布箱动作。
- 旧鼓于源 36/120 秒释放，新鼓 112/120 秒出现；插入、压实与空仓拉机柄沿用 201 原有接触时点。弹药资料刷新保留本次掉鼓状态，避免装填结算再次生成旧鼓。

## 可编辑源与复现

- `sources.json` / `Inputs/`：本次读取的当前 UE 网格、骨架、原生轨道、SHA-256 与来源路径。
- `LMG201_Drum46.blend` / `SM_LMG201_LargeDrum.fbx`：独立弹鼓模型。
- `LMG201_Drum46_Animated.blend`：当前枪体、V7 裸手及普通／空仓两条 base 全身 FK Action；其余四组完整本地轨道在 `Keys/`，并保存为可编辑 UE AnimSequence。作者场景不模拟运行时掉落实体，36–112 帧鼓显隐由游戏代码控制。
- `collect.py` → `read_geometry.py` → `author_model.py` → `author_animation.py` → `author_icon.py` → `install.py`；`author_scene.py` 保存动作编辑源，`finish_refresh.py` 仅更新新材质。
- `catalog.py` 只给 201 增加标准弹鼓选项并登记打包目录。
- 运行源码：`LMG201WeaponAssets.h`、`LMG201Attachments.h`、`M4DrumVisual.cpp`、`FPSGAMECharacter.h/.cpp`、`ColdSteelIconResources.cpp`。
- `install_receipt.json` 记录实际已保存资产；`delivery.json` 记录最终构建与未测试边界。首次资产保存日志为 `install_03.log`，后续材质取现用 J44 值的记录为 `finish_refresh.log`。

仅后台制作、导入、保存及必要构建。最终装配观感、手部接触及实机换弹由用户测试；没有修改原厂弹匣、布箱网格、既有动作和用户存档，也没有提交或推送 Git。
