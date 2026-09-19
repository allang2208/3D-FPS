# M4 扩容格纹统一（2026-09-19）

用户指出下方延长段与上方原厂纹路不是同一种风格，要求针对纹路重建。

## 最终制作入口

1. author_surface.py：从 Factory_M4 原厂外壳采样；按独立外壳表面取真实横筋和纵向凹槽，不用旧复制网格的三角面变形。内外壳按完整拓扑轮廓和包围尺寸区分，局部投射限定到外表面，避免穿过薄壳取到内壁或对侧。
2. finish.py：保留原厂未改区域的角点法线，新增密集网格用实际表面法线；重算接缝 UV 与切线空间法线变换数据。
3. render.py：统一前左向产品图标；install.py 和 install_icon.py：只导入本轮 M4 网格及其两个图标。

未采用的 author_grid.py 和未接入游戏的 M4ExtMagNormals20260919 已归档至 trash/extended-magazines-20260919；详见发布清单。

## 最终资产

- 可编辑源：M4_ExtMag40_Grid_Editable.blend（Factory_M4 源参见 ExtMagRebuild20260919 原厂保留对象，其源为 M4HK416Replica20260910）。
- FBX：FBX/SM_M4_ExtMag40_Grid.fbx。
- UE：/Game/Weapons/M4GridUnified20260919/SM_M4_ExtMag40_Grid。
- 沿用 /Game/Weapons/ExtMagContinuity20260919/Materials/M_M4_Continuous，以及既有干湿映射。
- 原厂弧长 111.5 mm 处延长 62.5 mm，格纹周期 12.5 mm。新增段使用 24 个采样站/周期，局部小幅平滑采样阶梯；保留上部插接、抓握和原底板。
- 容量、换弹动作和其它枪械不变。

## 本轮检查范围

按用户“继续检查调整”执行了 M4 局部法线量测和离线模型/材质对照。旧模型部分接缝角点法线差约 165 度，整下段重算法线也破坏了原厂平整面/倒角着色。用户随后将重点转为格纹统一，最终交付以上述表面重建为主。

完成导入及必要构建；未运行 PIE、未测试实际换弹/抓握。用户随后看最终预览并确认成功；该认可不扩展为实机换弹、抓握或天气测试通过。
