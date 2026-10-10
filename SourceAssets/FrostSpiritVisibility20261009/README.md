# 寒晶精神迸发：可见度修订（2026-10-09）

用户反馈寒晶双手剑的专属「精神迸发符文」看不见。本次按武器技能中的剑身符文与模块化近战规则，读取当前装配源码及已保存资产，修订这一份专属材质。未启动交互编辑器、PIE 或游戏，也未截图或进行视觉验收。

## 排查证据

- `MeleeRuneVisual.cpp` 按 `ue_frost_crystal_sword` 与 `spirit_burst_rune` 选择独立 `M_SilverRuneSurface_FrostSpirit`，模式为 4，沿用侵蚀裂纹遮罩；没有发现此选项的专门隐藏开关。其材质名仍能通过刀刃识别。
- `read_state.py` 用无界面 NullRHI commandlet 读取实际资产；`state_before.json` 记录原装、加长、厚脊和轻刃四种刀刃均存在、Nanite 均关闭，安装材质与各自投射尺寸保留。
- 现役 HLSL 为 `MeleeRuneFade20260922` 修订：裂纹最低权重 0.07，再乘 0.56 的 SpiritOpacity、呼吸衰减及局部遮罩，非迸发时核心覆盖率可低到约 3%；发光另有 1.15 的硬编码峰值上限。冰蓝与剑体同色，低覆盖率削弱辨识度。这是源码中的淡化事实，尚未通过运行画面证明为唯一原因。
- 保存资产的传统 Emissive/Opacity 输出存在，Substrate FrontMaterial 未显式连接。UE 5.8 支持隐藏材质转换，因此不能仅凭 FrontMaterial 为空断言材质完全不渲染。本次补上明确的 Unlit Substrate 输出，保持原曝光与透明度输入。

## 本次修改

仅更新 `/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit`，保留原冰蓝配色、三处聚能节点、约 3.70 秒循环、两次扩散回响、错峰与收边。

- `SpiritOpacity`：0.56 → 0.78，提高纹样覆盖率。
- 新增 `SpiritRestOpacity=0.14`：只对原裂纹遮罩保留低亮底纹；外围及剑根剑尖仍随原遮罩渐隐。
- `SpiritBrightness`：1.35 → 2.65；峰值改用已有 `EmissionPeak=2.4` 参数，RGB 等比限制，保持色相。
- 适度提高裂纹和圆润节点的基础权重，双波纹继续平滑出现、扩散与淡出。
- 将原 `EyeAdaptationInverse` 发光与 Alpha 遮罩接入 `MaterialExpressionSubstrateShadingModels` 的 Unlit 分支和 FrontMaterial；没有删除、重建整张材质图。

本次没有改动伤害倍率、其他武器的共用符文、网格、动作、存档或全局曝光。现有 `MeleeRuneVisual` 不覆盖上述精神迸发专用参数，因此不需要修改 C++ 或构建游戏模块。

## 制作与落盘

- `prepare_source.py`：从本次实际材质快照生成 `spirit_visible.hlsl`，保留投射、颜色和采样逻辑。
- `parameters.json`：本次专属参数。
- `install_material.py`：只更新并保存这一项材质；保留中途出现的未知材质编辑，修改前备份到 `Before/`。可用于无界面 commandlet，也可经现有编辑器互斥桥执行。
- `install_receipt.json`：只有实际编译及保存成功后写出，记录资产、参数、输出节点与保存散列。
- 旧制作目录仍是历史/恢复输入，后续重建该符文以本目录安装器为最后一步，避免旧淡化配方覆盖新版。

运行观感未测试，由用户测试。重新进入游戏或重新装配该改造后，观察待机时的冰蓝裂纹底纹与循环双波纹；若仍完全不可见，需要继续定位实际运行实例与覆盖层绘制阶段，不能把保存成功当作视觉故障已解决。

## 实际完成状态

2026-10-09 09:31 后台 commandlet 已保存正式材质包。构图节点改接期间出现的 `SpiritRestOpacity` 缺失输入警告属于参数尚未接齐的中间状态；最终不能只以即时 recompile 返回值认定着色器完成。

随后用户已有的编辑器/PIE 会话加载到新版材质。通过互斥桥只读调用 `get_statistics` 等待该材质的着色器任务，取得有效已编译像素着色器（425 条指令；不是性能测量）。`loaded_material_build.json` 与安装回执中的 `shader_compilation_finished=true` 记录此结果。

同次只读定位到当前 `ModularSwordBlade` 使用厚脊刀刃、可见状态为 true，实际 Overlay 为精神迸发 MID，RuneMode=4；运行实例已读取 SpiritOpacity=0.78、SpiritRestOpacity=0.14、SpiritBrightness=2.65，以及厚脊尺寸 13.68 / 10 / 63。说明当前实例没有被显示开关隐藏，且已取得新版参数；仍不代表图像观感已经验收。

没有启动、停止或操作这段已有游玩，也没有重新应用装备、改写存档、截图或视觉测试。材质图与参数已实际落盘，不需要 C++ 构建。
