# PKM Finish20 — 微划痕与雨天材质补齐

日期：2026-09-23。范围是当前 PKM 材质及雨滴覆盖，未调整几何、骨骼、动画、槽序或配件挂点。

## 当前资源

- 主体：`/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular`。
- 脚架：`/Game/Weapons/PKMLowpoly20260922/Bipod07/SM_PKM_Bipod`。
- 24 个改造件网格：`/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes`，包括活动倍率环。
- 新材料与干湿变体：`/Game/Weapons/PKMLowpoly20260922/Finish20/Materials`。
- 独立雨滴映射：`/Game/Weapons/PKMLowpoly20260922/Finish20/DA_PKM_WetMaterials`。
- 几何可编辑源仍是 `../OutgoingBelt19/PKM_OutgoingBelt_Editable.blend`；这次材质升级在 UE 材质图中完成。

## 制作处理

保留当前深色枪钢、木材、聚合物、橡胶、弹壳与钛色部件的身份。增加稀疏短划痕和轻微表面反射变化；细节主要改变粗糙度和极小的底色/金属反射，不覆盖原有结构法线和 AO，不增加大面积银白破损。

`MicroFinish.hlsl` 按蒙皮前局部厘米坐标投射，两个网格尺度为 1.8 cm 和 2.8 cm，导数抗锯齿。位置与法线经 VertexInterpolator 进入像素阶段，防止动画时划痕在表面滑动。UV0 和原纹理采样维持原样。`PKM_MicroScratchStrength` 默认：金属 .34、木材 .12、聚合物 .10、橡胶 .025、弹药 .08、内腔 0。

所有修改均为 PKM 专用副本，未改写跨枪共享母材质。实例原有标量、向量与纹理覆盖保留。91 个材质槽原名与原序保留，避免破坏换弹分件隐藏和枪匠装配。

## 雨滴覆盖问题与修复

修改前按运行时聚合的天气映射查询，82 个相关表面槽仅 2 个有映射，PKM 私有枪体与大部分改造件缺失。现在 55 组干湿材质覆盖 82 个表面槽；其余 9 槽为手部、镜片和分划，维持原样。

混合光学/设备材料复用原外壳分区，保留镜片、刻字与发光输出。激光器排除现有发光口；手电使用现有外壳/尾盖遮罩。湿层保留结构法线，仅叠加细小水珠法线、湿润暗化和粗糙度变化。增加湿度为零时的水珠归零，确保干燥时没有水珠残留。

`PKMLowpolyWeaponAssets::WetMaterialsPath` 与 `UWeatherViewEffectsComponent::Initialize` 合并本枪独立表。现有绑定逻辑覆盖主网格及其递归附属网格；换改造件时会重新识别材质。继续使用按武器实例累计的 `WeaponWetness`，受降雨强度、遮挡、天气质量和 `fps.WeaponWetness` 开关控制。

这次补齐的是现有水珠与湿膜，不包含新增水滴下滑动画。

## 作者入口与记录

- `read_materials.py` / `materials_before.json`：修改前实际绑定、材质图与映射记录。不要在新版本上覆盖此快照。
- `build_finish.py` / `finish_import.json`：生成/更新干湿材质、保存独立表、实际替换指定网格槽。
- `check_saved_materials.py`：用户要求范围内的保存资产读回、槽序/雨滴图连接核对和材质编译。
- `material_rain_check.json`：保存资源核对结果，26 个网格、91 个槽，82 个表面槽全部有雨滴映射；55 对干湿材质的湿度连接、干燥归零、法线/AO 纹理和实例覆盖检查无缺项。
- `check_saved.log`：110 个干湿母材质在 PCD3D_SM6 后台编译，返回编译错误数均为 0；commandlet 退出码 0。
- `build_cpp.log`：本次普通 Editor 目标后台构建记录。

普通 Editor 目标构建已成功，构建日志 `Saved/BuildEditor/build-20260923-090657.log`。新材质、独立雨滴表、26 个网格的实际绑定均已落盘，原生天气表合并已进入构建产物。

未启动交互编辑器、PIE、雨天场景或渲染。材质资产检查和必要构建不代表实机雨滴大小、高光与划痕观感已验收，实际显示交由用户测试。
