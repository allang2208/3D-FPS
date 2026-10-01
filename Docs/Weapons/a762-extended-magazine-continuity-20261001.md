# A762 扩容弹匣 Continuous07（2026-10-01）

本轮针对用户指出的下段弯曲角度与明显拼接面问题，沿用 `skills/ue5-weapon-workflow/references/extmag-lengthening.md` 的曲线、截面和纹路连续方案。材质继续使用 [Refine06](a762-finish-refine06-20261001.md)。

## 改动

旧 `Accessories05/author_geometry.py` 按每个顶点的世界高度做 Y/Z 偏移，令底部截面从原厂约 60.8 mm 变为 71.8 mm，底板与下段轮廓因此失真。新版本从 A762 原厂曲线重建：保留前 80 mm 曲线及截面，在后段增加 42 mm 弧长，平滑分配曲率变化，末端截面恢复为原厂约 60.8 mm。

- 保留原厂供弹唇、前后卡榫、托弹板和底板。底板沿新曲线移到末端，保留原厂末端切线方向。
- 壳体为单块连通曲面，纵筋和侧板起伏直接进入表面，避免重叠环带或硬拼接套。
- 横筋按实际弧长延续完整单元，下段节距约 14.98 mm；不把既有纹路整体拉长。
- 主壳 UV 按既有约 0.35 UV/cm 的物理尺度连续展开；口缘和封底使用二维投影及扇形三角网，消除封底塌缩 UV。
- 不改变装配原点、弹量、骨骼、换弹动作、枪械代码及三槽材质绑定。

以上尺寸用于本项目模型的比例与形状修正，不表示真实武器工程规格。

## 制作与保存

作者目录：`SourceAssets/A762ExtendedMagazine20261001/`。

- 源：`A762Meshy20260920/Refinement04/A762_StockJoint_Editable.blend`。
- 制作入口：`curve.py`、`author.py`。
- 可编辑成品：`A762_ExtMag_Continuous07.blend`；导出：`Exports/SM_A762_ext_mag_Continuous07.fbx`。
- 独立修订：`/Game/Weapons/A762/ExtendedMagazine20261001/SM_A762_ext_mag_Continuous07`。
- 游戏原运行路径：`/Game/Weapons/A762/Accessories05/Meshes/SM_A762_ext_mag`。
- 保存入口：`install.py`；`save_final.py` 在同一批次保存并读取运行资产的几何。
- 原资产备份：`Before/SM_A762_ext_mag.uasset`；保存散列、导出散列、绑定及完成状态：`install_receipt.json`。

FBX 导出前显式三角化。独立修订关闭导入参数及静态网格 LOD0 构建设置中的 `remove_degenerates`，导入作者法线并重新生成 Mikk 切线。旧运行包直接 FBX 重导入后仍出现细面丢失；提前修改构建标志也未能解决。因此最终运行资产使用 `continuous_mesh_copy_v1`：从独立修订读取完整源几何，经 GeometryScript 写回原资产，并传递 UV、法线和三个材质槽。写入前要求源面数与作者记录一致。

仍绑定 `SurfaceStandard08/Accessories/Materials/` 下的三个 `MI_A762_WS_ext_mag_*` 实例：主壳、内腔和边缘。父材质、微法线、粗糙度配方与天气接入继续沿用 Refine06，没有新增母材质或天气分支。

旧配件作者入口在本轮安装完成后复用 Continuous07 FBX。后续保存使用本目录入口；旧材质安装脚本会清空 Refine06 覆盖，不应直接重跑。

## 定向检查与交付边界

本次用户明确要求检查弯曲与拼接。离线侧面对照见 `SourceAssets/A762ExtendedMagazine20261001/curve_comparison.png`：左旧版，右新版；它不是游戏截图，也没有使用游戏中的完整照明与材质。

制作源及 UE 读取数据分别记录在 `inspection.json`、`CandidateGeometry/`、`SavedGeometry/`。`measure_saved.py` 只测量此次相关的表面开边、三角形和 UV；最终运行资产的数据以 `SavedGeometry/seam_measurements.json` 为准。

**最终版已于 2026-10-01 13:37 保存到上述运行路径。** 最终回读为 57,982 个顶点、115,936 个三角面，与作者面数一致；在 1e-6 cm 同位置合并口径下开边 0、非流形边 0，零面积面 0、塌缩 UV 三角面 0。三个 Refine06 材质槽继续对应原实例。运行资产 SHA256 为 `93406d0b394b30b0f87e91de21d85d6fc144483a3630dc7beff9097a2fff7fc8`。

保存日志：`SourceAssets/WeaponSurface20260930/logs/save_final.20261001-133654-957.log`，命令行进程退出码 0。后台启动期间曾等待项目占用，并遇到 SDK 扫描等待及 Zen 启动中断；最终仅对本次进程设置 `UE_SKIP_UBT_SDK_SETUP=1`，并使用入口的 `-FileCache` 文件缓存选项完成写入，没有修改引擎或项目的全局缓存配置。

未启动游戏、未进行换弹或雨天运行测试，实机视觉与动作由用户测试。单块闭合几何及保存成功不等于用户已认可最终视觉效果。
