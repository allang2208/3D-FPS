# 墙面细微凹凸恢复（2026-09-24）

> 用户反馈此轮仍无可见变化。当前实现已由 [后续排查与修复](dungeon-wall-relief-followup-20260924.md) 替代：补齐原先漏掉的上方混凝土墙，砂浆恢复完整配套表面并改用不依赖模型 UV 的坐标。本文保留第一轮制作记录，不代表当前最终效果已获验收。

## 原因

用户记忆对应 9 月 22 日的 [墙面剥落基层与凹凸版本](dungeon-wall-relief-20260922.md)：复用丘陵材质的近景视差方法，以原创 16-bit 高度场表现砂浆、残余粘结层、砂粒和刮痕，法线及粗糙度来源与高度一致。

9 月 23 日的 `DungeonWallDamage20260923/Scripts/create_materials.py` 将旧 `MI_WallMortar_Bed` 和 `MI_WallMortar_Finish` 一并映射到 Fab 混凝土实例。该主材质只有扫描底色、法线、ORM，没有高度输入或视差步进；对应制作文档明确记录了“不启用逐像素多步视差”。这是本次追溯发现的效果丢失节点。9 月 24 日的 ISM/Nanite 使用标记修复解决缺省材质问题，没有恢复这一材质功能。

随机剥落版本仍保留连续砂浆基层及毫米级几何起伏，但网格间距从旧版 2.5 cm 改为约 5 cm。小颗粒、刮痕的细节由原有高度图与法线承担，本次恢复这部分，不重建墙面几何。

## 修改

- 新主材质 `/Game/Dungeons/WallDamage20260923/Materials/M_FabWallMortarRelief20260924`。
- 原地接回两个现用实例 `MI_FabExposedBed`、`MI_FabBondingMortar`；墙面模型和随机目录继续引用相同实例路径，无需重新绑定地图。
- 复用原有 2K Half Float 高度、配套法线与粗糙度/AO/覆盖纹理。保留用户指定 Fab 扫描的底色、法线和 ORM；没有从扫描图的明暗推造高度。
- 使用这些砂浆材质槽现有的 1.28 m 作者 UV。视差交点换算为物理偏移，再同时应用到 Fab 色彩、法线、粗糙度和砂浆各通道，避免只有颜色移动。
- 基层高度范围恢复 0.65 cm，粘结层/填缝 0.065 cm；后者法线强度为基层的十分之一。实际高度纹理取值没有占满整个标称范围。
- 近景 7–12 次粗采样，最多 4 次交点细化；2.5–6.5 m 平滑渐隐，掠射角衰减。UV 梯度在步进前计算，用于稳定 mip 选择。无需三向各走一遍视差。
- 两套法线合成保留颗粒与薄层细节；AO、覆盖及粗糙度使用配套高度表面的数据，弱化重复色差。
- 保留 ISM/Nanite 使用标记。不接世界位置位移或像素深度偏移，不改墙体轮廓、门框、瓷砖厚度或碰撞。
- 指定 Fab 破墙截面 `MI_FabBrokenConcrete` 继续使用扫描材质；本次恢复的是曾被替换掉的砂浆层。
- 原 Fab 材质制作入口复用本次材质生成函数，后续重建不再把这两个实例切回没有高度的主材质。

## 制作与交付记录

作者脚本和着色器：`SourceAssets/DungeonWallReliefRestore20260924/Scripts/`。

`Before/Content/` 保存被修改实例的原始包；`Receipts/install.json` 记录实际落盘父材质和参数。只有 `stage=materials_saved` 才表示两个实例已保存。

必要 HLSL 构建使用 Windows SDK DXC，对实际 Custom 节点函数体编译 SM6；结果写入 `Receipts/shader-compile.json`。这不等于 UE 全部材质排列已编译，也不等于运行画面或性能验收。后台 NullRHI 的 `recompile_material` 不作为渲染成功证据。

本次实际保存完成：一个新主材质、两个现用材质实例，`Receipts/install.json` 为 `materials_saved`。保存回读确认两个实例此前均指向 `M_FabExposedConcrete`，现在均指向新版凹凸主材质，深度分别为 0.65 / 0.065 cm。第一次后台执行遇到 `Material` 不暴露 `desc` 属性，发生在资产保存前；改用已有的包元数据接口后，第二次 commandlet 正常结束，退出码 0（`install-commandlet-02.log`）。DXC SM6 函数体编译退出码 0。

没有启动交互编辑器、游戏、PIE、截图、渲染或性能测试；最终效果由用户测试。
