# PKM 表面升级 R01 — 2026-10-01

已完成后台制作、材质编译与实际资产保存。52 个实例、50 个保留源图集分区的私有适配母图、1 张细纹贴图，更新 28 个现用网格的材质绑定。没有打开交互式 UE、运行游戏、截图、渲染或测试。

## 输入与范围

当前输入是用户提供的低模 PKM 分支 `PKMLowpoly20260922`，不是已退役的 Meshy PKM。主网格仍为 `/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular`；`Input/current.json` 保存制作前实际槽、源图、有效参数及天气映射。

沿用 WS1.1 的干净深色处理金属外观与亚毫米细纹方法。机匣、活动钢件、枪口、安装座、脚架及枪托金属各有可调实例；现有聚合物、橡胶另设表面响应。新旧弹药箱共用独立军绿色漆面，完整漆面 Metallic=0。本项目深色金属配方不作为裸金属实测反射率。

木质件、V7 手臂、弹链及弹药、镜片与分划、光学保护区域、内腔和钛色饰件保留。主网格机匣与盖体仍共用原槽，本轮没有拆槽或声称分别重建。旧 Accessories14 的 optic_rail 不在当前运行入口，本轮保留，正式导轨按 OpticMount23 更新。

## 制作方法

- `produce.py`：制作 1024² 线性 RGBA 技术纹理和逐槽配方。R 细金属颗粒、G 小范围变化、B 无划痕、A 聚合物细纹；4 cm 三向平铺，使用原蒙皮前局部位置／法线插值。
- `apply_finish.py`：复制各源湿材质图作为私有适配图，在原基础涂层节点内替换颜色和粗糙度，不叠加第二层水膜。保留源 UV0、结构法线、AO、材质区域、光学遮罩、有效实例参数及静态开关。
- 新实例本身包含原有 `WeaponWetness` 与水珠层，在既有 Finish20 天气表中增加 52 个自身映射；旧映射保留。
- 静态／骨骼用途分别制作适配图；静态配件不继承 skeletal、morph、cloth 用途。新图 BC7、Weapon LOD Group、mip 和流送正常保留。
- `Before/` 保存 28 个目标网格及天气表原包；旧材质及贴图没有覆盖。`BeforeScripts/` 保留旧缎面安装入口。

## 当前制作入口

- `recipe.json`、`Textures/`、`apply_finish.py`：本轮生产配方与初次接入。已完成时不为自测重跑。
- `apply_receipt.json`：实际保存回执，`complete=true`、`geometry_changed=false`、`tested=false`。
- `finalize_records.py`：从已完成回执写 `bindings.json` 和 `SourceAssets/PKMLowpoly20260922/current_surface_bindings.json`。
- `rebind_current.py`：以后明确执行旧导入时恢复当前材质引用，不重建材质或网格；独立修改过的槽不覆盖。
- 原 `PKMRefinedFinish20260927/install_finish.py` 已根据当前清单转到新引用恢复入口。主网格 `Belt08/material_binding.py` 和脚架 `Bipod26/import_assets.py` 从同一清单选材质。

保存日志：`SourceAssets/WeaponSurface20260930/logs/apply_finish.20261001-160943-720.log`，commandlet 退出码 0，输出 `WEAPON_SURFACE_PKM_R01_SAVED 52 instances 50 adapters 28 meshes; geometry_changed=False; tested=False`。

这不是减少母图数量或游戏性能提升的声明；50 个私有适配图保留了源图集、分区与结构输入。未做游戏或视觉验收，最终效果由用户查看。
