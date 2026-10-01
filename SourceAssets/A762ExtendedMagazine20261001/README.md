# A762 扩容弹匣 Continuous07

目标是修正旧扩容弹匣下段角度与截面失真，并避免横向拼接带。规则沿用 `skills/ue5-weapon-workflow/references/extmag-lengthening.md`。

## 来源与做法

- 实际旧网格：`/Game/Weapons/A762/Accessories05/Meshes/SM_A762_ext_mag`；读取副本在 `Input/`，保存前资产散列与 Refine06 材质绑定在 `Input/current.json`。
- 原厂源：`SourceAssets/A762Meshy20260920/Refinement04/A762_StockJoint_Editable.blend`，弹匣曲线来自其 `Refinement02/rebuild.py`。原厂供弹唇、卡榫、托弹板和底板保留为真实源几何。
- 旧方案按世界 Z 高度分别偏移顶点 Y/Z，令下端截面由约 60.8 mm 放大至 71.8 mm，并改变截面角度和纹路间距。
- `curve.py` 保留原厂前 80 mm 中心线与截面，沿曲线增加 42 mm 弧长。后段平滑延续切线及截面变化；这是曲线参数重建，不是将旧网格做 smoothstep 拉伸。
- `author.py` 生成单块连通壳体，纵筋和侧板起伏直接构成壳面。下段横筋按约 14.98 mm 实际弧长节距添加完整单元，底板保持原厂形状并移到末端。
- UV0 按物理尺度连续铺设，封底／口缘使用有效二维投影。相同金属实例和弱微法线继续使用；没有横向 UV 岛拼接，也没有覆盖一圈连接套。

## 制作与接入

Blender 5.1 后台运行 `author.py`，输出 `A762_ExtMag_Continuous07.blend` 与 `Exports/SM_A762_ext_mag_Continuous07.fbx`。

通过项目现有批次入口运行：

```powershell
& .\SourceAssets\WeaponSurface20260930\run_ue.ps1 -Script 'D:\FPS3D\FPSGAME\SourceAssets\A762ExtendedMagazine20261001\install.py'
```

保存独立修订 `/Game/Weapons/A762/ExtendedMagazine20261001/SM_A762_ext_mag_Continuous07`，再应用到原运行路径。绑定始终按原三槽材质名称写回，保留 Refine06 实例；不修改 C++、弹量、动画或挂点。原 uasset 在 `Before/SM_A762_ext_mag.uasset`。

`install_receipt.json` 记录保存结果、文件散列与使用的 FBX 散列；`complete` 要求独立修订与运行资产均对应当前 FBX，独立修订使用 `keep_small_faces_preimport`，运行资产使用 `continuous_mesh_copy_v1`。旧配件批次作者入口已改为优先复用本轮已安装的 FBX。

导出前显式三角化，封底使用扇形三角网避免退化 UV。独立修订的导入数据与静态网格 LOD0 构建设置均关闭 `remove_degenerates`，保留作者法线并重新生成 Mikk 切线。旧运行包直接 FBX 重导入后仍出现细面丢失，最终改为读取独立修订的完整源几何，经 GeometryScript 写回原资产；写入前要求面数与作者记录一致，同时传递 UV、法线和三个材质槽。后续保存使用本目录 `install.py`，不要直接重跑会清空 Refine06 材质覆盖的旧材质安装批次。

## 本次授权的检查

用户明确要求检查弯曲和拼接问题，因此运行 `inspect_geometry.py` 的定向几何与离线侧面对照；`--measure-only` 只输出几何数据，不再渲染。`capture_saved.py` 读取最终 UE 保存网格用于定向核对。

`inspection.json` 与 `curve_comparison.png` 为离线模型检查证据，不是游戏画面，也不代表实机换弹／雨天通过。`CandidateGeometry/` 与 `SavedGeometry/` 是从 UE 读取的独立修订／运行资产；`measure_saved.py` 只核对本轮要求的表面开边、三角面与 UV。运行效果由用户测试。

最终运行资产于 2026-10-01 13:37 保存完成。`SavedGeometry/seam_measurements.json`：115,936 三角面与作者一致，开边／非流形边／零面积面／塌缩 UV 均为 0。完整交付记录见 `Docs/Weapons/a762-extended-magazine-continuity-20261001.md`。
