# 唐刀专属改造：璇云龙璧护手

`ue_tang_dao / guard / xuan_cloud_dragon`。按用户参考制作层叠璇云轮廓、龙首和龙身浮雕、云纹镂空及雕纹止滑环。实际凸纹进入双面几何，微小鳞片蚀刻与磨损进入 4K PBR；鎏金凸面配暗铜凹底，保留高低层次。

护手板面约 14.4 × 16.4 cm，承力板厚 8 mm，正面浮雕最高 2.5 mm，背面采用同样纹饰并稍降低高度。镂空为真实贯通孔，孔壁和外缘具有厚度；中央承力芯为实体，前后安装圈采用 TangDao 原有 123 / 215 顶点的真实接口轮廓。前端 Z=1.4 cm 衔接刀身，后端 Z=-5 cm 衔接握柄；枢轴和安装旋转延用原装护手定义。

## 制作文件

- `surface_recipe.py`：高度源转换、4K BaseColor / Normal / ORM 及可编辑 16-bit 高度图。
- `author_guard.py`：双面浮雕、层叠边框、贯通云孔、承力芯和止滑圈，以及三档距离 LOD。
- `TangDao_XuanCloudGuard_Editable.blend`：包含材质、UV 和 LOD 的可编辑模型；FBX / GLB 在 `Export/`。
- `render_menu_icon.py` / `TangDao_XuanCloudGuardIcon_Editable.blend`：实际模型的独立灰阶改造图标源。
- `import_assets.py`：实际导入并保存新资产，复制现有 TangDao Substrate 材质并绑定本护手 PBR，保留旋风期间的响应材质。
- `catalog_extension.py`：合并本护手选项、网格和材质引用，保留其他武器及唐刀刀身、符文和配重锤。

UE 资产目录：`/Game/Weapons/TangDao20261002/XuanCloudGuard20261002`。选项只对唐刀开放，限定金卡按明确的武器、槽位和 ID 接入。基础唐刀和 SurfaceV2 的重导入入口已增加本扩展，祥云符文仍在最后处理。

本次制作外观，`stats` 保持空值，参考图注释不直接转成未确认的战斗属性。来源、生成提示词、资产保存回执和构建结果均保留在本目录。

默认后台制作、导入、保存与必要构建。未启动 UE 编辑器或游戏，未进行运行测试、截图或验收；实际持握和改造预览由用户自行测试。完成状态以 `delivery.json` 为准。
