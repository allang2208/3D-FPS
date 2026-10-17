# 守寝者围布 V13（2026-10-16）

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

2026-10-17 用户反馈衣物仍不合格并要求剔除；V13 不作为认可模板。移除衣物及左手尖刺修复的当前进度见 `NightWardenBareBodyHandV14.md`。

状态：源模型、FBX、三套动画、物理布料和 BP_NightWarden 已保存。通过现有编辑器的批次互斥桥完成资产接入，没有启动编辑器或试玩。未渲染、未进行实机测试，视觉与穿模效果待用户确认。

## 本次处理

旧 V10 围布主要由骨盆带动，最大物理位移 20 cm，制作时使用的挥击仍是 V09。V13 使用当前 V07 行走和 V12 百目横扫的实际身体轨道重新制作衣物形变。

- **研究员 V04**：固定裁片坐标和身体对应关系，按实际蒙皮后的身体表面生成向外修形量，再作空间和时间平滑。避免每帧换绑造成布料跳动。
- **园艺师 V02**：连续裁片、侧开衩、成对内外表面和一致权重，保留 1.4 mm 布料厚度，使用连续 UV。腰口有独立叠布收边。
- **巫婆 Drape07**：复用已保存的下摆 Chaos 配置和项目自有稳定绑定实现，保留法线、切线捕获处理；固定主体，只让自由下摆进行次级运动。

研究员原流程的显示网格 morph 修形没有直接套到物理布料上。这里把同类修形写入 96 根独立衣物支撑骨骼，让显示网格和物理代理获得相同的基础形变。原身体 46 根骨骼的参考姿态、蒙皮和三套动作轨道保留。

显示网格沿用 V10 的身体与贴体遮挡内层；完整原始身体仍保留在 Blender 源文件中。新外层包覆腰胯，侧面下段开衩。修形分别依据待机 228 帧、行走 145 帧、百目横扫 85 帧制作。衣物骨骼的局部动画使用新 FBX 导入后的真实参考变换换算。

物理代理导入后为 930 个顶点，其中 576 个固定。自由下摆位移由固定区平滑增加到 3.2 cm；沿用 11 个身体与巨臂碰撞胶囊。新的独立骨架避免修改旧模型与旧动画的共享骨架。

## 已保存入口

- 蓝图：`/Game/Monsters/NightWarden/BP_NightWarden`
- 模型：`/Game/Monsters/NightWarden/V09Melee/TailoredWaistV13/SK_NightWarden_TailoredWaist_V13`
- 动画目录：`/Game/Monsters/NightWarden/V09Melee/TailoredWaistV13/Animations`
- 物理代理：`/Game/Monsters/NightWarden/V07WaistStride/TailoredWaistV13/SK_NightWarden_HemProxy_V13`
- 原入口和 F6 守寝者条目保留。已生成的旧实例应重新生成后查看新版。

步速基准仍为 177.3769 cm/s，使用现有实际移动速度驱动步频；转身速度仍为 Yaw 100 度/秒。百目横扫原身体动作、AI 行为和命中时间窗 0.54–0.73 秒保留，本次只替换带衣物形变的对应动画资产。

## 制作与保存记录

- 源文件：`SourceAssets/NightWarden20261015/V13TailoredWaist/Authoring/NightWarden_TailoredWaist_V13.blend`
- 导出：同级 `Exports` 目录。
- 修形与动作输入：同级 `Motion/supports.json`，引用当前身体动画的原始键数据。
- 保存回执：同级 `Records/ue_delivery.json`，`complete=true`，保存了模型、代理、骨架、三套动画和蓝图。
- 布料回执：同级 `Records/cloth_binding_f94018e09cec4d129adb00a404e9e087.json`。
- 蓝图备份：同级 `Records/BP_NightWarden.before_v13.uasset`。旧版本模型、动画和骨架未删除。
- 制作脚本：`SourceAssets/NightWarden20261015/Scripts/author_tailored_waist_v13.py`。
- 导入脚本：`SourceAssets/NightWarden20261015/Scripts/install_tailored_waist_v13.py`，入口 `v13_background.ps1`。

本次没有新增插件依赖、购买外部软件或改动运行时 C++。制作与保存回执不代表动态混合、急转身或连续攻击已通过实机验收。
