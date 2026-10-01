# M16 材质统一 R01（2026-10-01）

## 制作状态

按 AKM、HK416、M4 的表面统一方式，保留 M16 原作者纹理，对主枪和专属配件配置金属与聚合物层次。

已保存 66 个材质实例、60 个私有材质适配图和 1 张细微粗糙度纹理，并完成 29 个网格、74 个材质槽及湿润映射表的发布。第一次后台保存被共用 Content 的 FPSGAME-mp 编辑器占用阻断；用户关闭该编辑器后，沿同一回执续存完成，`apply_receipt.json` 的 `complete` 为 true。

## 接入范围

- 主枪：`/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny`，13 个枪体材质槽。
- M16 UniversalAttachments20260920 中的 25 个网格，包含扩容弹匣、大弹鼓、握把、枪托、枪口、光学器件和辅助瞄准配件。
- ARParts20261001/M16 中的 HK416 枪托与后握把适配件，共 2 个网格。
- CommonHK41620260930 中的 M16 专用 EOTH 全息瞄准器，共 1 个网格。
- 合计 29 个网格，即主枪与 28 个专属配件网格；已合并 66 条新实例湿润自身映射。
- 新资产目录：`/Game/Weapons/M16A2/SurfaceStandard20261001`。

多口径消音器使用跨枪械的 `SM_Common_multi_caliber_suppressor`，本次保留其共用材质。独立玻璃、准星、橡胶、凹槽、镜筒内壁、钛装饰和手臂皮肤槽保留。

## 表面配方

原厂 M16 已有金属度/粗糙度 PBR 输入，直接保留原 BaseColor、金属度、Normal、AO 和 UV，不套用 M4 旧 Phong 转换。遮罩保留原涂装、刻字、划痕和磨损；只调整被选区域的表面色调、明度对比及粗糙度。

金属粗糙度中心为机匣 0.35、护木 0.38、机械件 0.30、弹匣 0.31、接口 0.40、枪口 0.44、光学外壳 0.37、枪托/后握把 0.39、其他配件 0.38。叠加原粗糙度细节和细微表面变化，避免各处呈同一种平涂亮度。

聚合物粗糙度中心为弹匣/弹鼓 0.43、护木 0.50、枪托/握把及普通配件 0.49、其他区域 0.42。大弹鼓的外壳、紧固件和索引区域三类源材质均纳入配方，同时保持金属与聚合物身份。

全景红点外壳此前仍接旧 M4 涂层。本次在私有图内将该涂层输入改接 M16 的 BaseColor、Metallic、Roughness，继续使用 UV3；源表面分支、标记遮罩、Normal 和 AO 保留，不修改共用 M4 原图。

## 湿润与入口

私有图解除旧湿润包装后接入一层统一湿润响应；无既有湿润层的主枪补上 `WeaponWetness` 输入。颜色、粗糙度与法线保留单层响应，零湿润度不残留水珠。

发布目标天气表是 `/Game/Weapons/M16A2/UniversalAttachments20260920/DA_M16_AttachmentWetMaterials`，合并新增实例自身映射，保留已有映射。实际游戏与改造预览继续使用原网格路径；本次不改 C++、网格形状、骨架、动画、安装接口或枪械数据。

## 后续重新导入

`M16/current_bindings.py` 按精确网格路径应用当前材质清单。已接入 M16Gameplay、M16UniversalAttachments、M16Refinement、M16RecoveryStocks，以及 HK416UniversalParts、HK416FactoryParts 的导入保存入口，后两个仅匹配 M16 专用网格。M16 UniversalAttachments 天气表发布改为合并已有映射。

这些旧全量导入脚本本次未执行；只修改其后续导入行为。全部资产续存完成后，`finalize_records.py` 已发布 `current_surface_bindings.json`，后续重新导入可恢复本次材质绑定。

## 文件与来源

- 制作目录：`SourceAssets/WeaponSurface20260930/M16/Refine01/`。
- 输入快照：`Refine01/Input/current.json`；配方：`Refine01/recipe.json`。
- UE 保存回执：`Refine01/apply_receipt.json`；修改前备份：`Refine01/Before/`。
- 续存入口：`SourceAssets/WeaponSurface20260930/M16/run_finish.ps1`。
- 首次保存日志：`SourceAssets/WeaponSurface20260930/logs/apply_finish.20261001-201125-817.log`。
- 完成日志：`SourceAssets/WeaponSurface20260930/logs/apply_finish.20261001-201835-481.log`。后台 commandlet 正常退出，输出 `WEAPON_SURFACE_M16_R01_SAVED 66 instances 60 adapters 0 runtime override materials 29 meshes; geometry_changed=False; tested=False`。
- M16 原模型和纹理署名仍见 `SourceAssets/M16A2Migration20260919/ATTRIBUTION.md`：Luchador 原枪、user77 来源包；本次沿用本地来源链。
- HK416 派生配件沿用原 MojoLeeDa 来源记录，不增加外部资产。

本次只进行制作所需的资料读取、材质编译、导入与保存。不主动启动 UE 界面或游戏，不运行测试、预览、截图渲染及验收。实际外观由用户测试。
