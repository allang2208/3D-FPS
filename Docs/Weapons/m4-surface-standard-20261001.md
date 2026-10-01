# M4 材质统一 R01（2026-10-01）

## 已保存范围

延续 AKM、HK416 的原作者表面保留方案，处理当前 M4 主枪和 29 个配件网格，共 30 个网格。材质制作和实际绑定均已保存；没有网格重导，没有修改骨架、动画、安装位置和枪械数值。

- 主枪仍为 `/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416`。
- 配件覆盖机瞄、前握把、后握把、枪托、光学瞄具及倍率环、普通/战术消音器、制退器、扩容弹匣、大弹鼓、手电、激光器和 M4 专用 416 枪托/后握把。
- 新资产位于 `/Game/Weapons/M4/SurfaceStandard20261001`，含 41 个实例、33 个私有材质适配图、14 张生产纹理。
- 2 个 M4 专用运行时覆盖材质在原路径更新：手电 `M_M4_flashlight_Body_MetalTail` 和激光器 `M_M4_laser_Body_OpticalV2`。保留其光学/发光支路，并同步保存网格槽绑定。

## M4 的原始 PBR 接入

M4 主体原先使用 `FBXLegacyPhongSurfaceMaterial`：Roughness 图作为 Shininess 输入，而原作者 Metallic 图没有接入当前材质。附加涂层的粗糙度纹理还使用 sRGB 采样。这些转换不能直接套用 HK416 的金属度遮罩配方。

本次从现有 `Content/m4noskel.fbm` 导入 Body、Keymod material、Magazine Light、Flash Hider、Grip Default、Classic Stock 的 Metallic/Roughness 源图，共 12 张，保存为 M4 私有线性纹理。原 BaseColor、法线及 UV 接线沿用现有来源；扩容弹匣保留连续 UV 的现用图结构。

私有图绕过 Phong 的颜色/粗糙度/金属度转换，接回作者的线性粗糙度和金属度。配件沿用已有金属区域遮罩，将该涂层分支改为金属响应，其余区域保留原有分区。共用的机匣涂层 Roughness 复制为私有线性版本，原纹理不修改。另使用 1 张 4 cm 物理尺度的细微粗糙度纹理。

原装轻型弹匣和握把的作者 Metallic 图为非金属；它们采用聚合物响应，不因统一枪身风格而强行金属化。枪身涂层、露出的金属、聚合物、橡胶、镜片和钛色饰件保持分区。

## 表面配方

金属粗糙度中心：机匣 0.34、护木 0.36、弹匣金属区域 0.31、接口 0.40、枪口 0.43、瞄具外壳 0.37、枪托等 0.39、其余配件 0.38。保留源粗糙度细节，再加低强度细纹。

非金属另有配方：原装弹匣/弹鼓外壳 0.43，机匣的涂装区域 0.38，护木的涂装区域 0.40，握把/枪托约 0.49。保留源图差异，并通过亮度和色彩遮罩降低对彩色涂装、亮色刻字、划痕和极暗凹槽的调整幅度。大弹鼓三个槽均接入现用新实例，避免只改到扣件。

玻璃、准星、橡胶、枪口内腔、钛色饰条和手臂皮肤槽保持原材质。本次没有重画装饰、替换原法线或修改几何细节。

## 湿润与运行入口

新私有图保留单层 `WeaponWetness` 湿膜，已有湿膜图先取干燥输入再接统一表面；新增图只添加一层湿膜。天气表 `/Game/Weather/RainVisibility/DA_WeatherPresentation` 合并 43 条自身映射，并保留其他枪的既有映射。

枪身与配件使用当前运行时网格路径，手电/激光器的 C++ 覆盖路径也已处理；无需修改 C++ 或重编译原生模块。改造预览和实际角色均继续使用现有装配入口。本次未执行游戏测试，因此不将保存状态视为运行时视觉验收。

## 制作源、回执与重新导入

- 制作源：`SourceAssets/WeaponSurface20260930/M4/Refine01/`。
- 输入快照：`Input/current.json` 和 `Input/source_contracts.json`。
- 配方：`recipe.json`；执行：`apply_finish.py`；实际保存回执：`apply_receipt.json`。
- 修改前网格、运行时覆盖材质和天气表备份：`Refine01/Before/`。
- 已发布绑定：`SourceAssets/WeaponSurface20260930/M4/current_surface_bindings.json`。
- 重导绑定函数：`M4/current_bindings.py`。主枪 Replica、M4GridUnified 扩容弹匣、LargeDrumUpgrade 弹鼓和 WeaponAttachmentFinish 通用配件导入入口已接入；本轮未运行这些历史全量导入脚本。
- 必要的保存入口：`M4/run_finish.ps1`，沿用公共 UE 桥/commandlet 批次互斥，且在共享 Content 的联机游戏运行时暂缓写入。

首批保存时，共享 Content 的两个联机后台实例占用了主枪包。材质、纹理和天气表已落盘，主枪保存失败后保留回执与备份；实例退出后续接剩余绑定，没有终止其他进程或发送跨任务消息。

最终生产日志：`SourceAssets/WeaponSurface20260930/logs/apply_finish.20261001-200602-200.log`。commandlet 退出码 0，输出 `WEAPON_SURFACE_M4_R01_SAVED 41 instances 33 adapters 2 runtime override materials 30 meshes`。

仅执行必要输入读取、制作、材质编译、导入和保存。未启动游戏、PIE、截图渲染或追加测试；实际观感交由用户测试。
