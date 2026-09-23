# PKM 通用改造件接入（Accessories14）

后续模型源更新（2026-09-23）：当前模块化枪体新增木制提把铰轴，最新网格作者源位于 `../CarryHandle18/PKM_CarryHandle_Editable.blend`。不要用本目录旧整枪导出覆盖该版本；配件、材质及游戏路径仍沿用本目录的接入。

后续修订：前握把腕臂姿态与三款后握把安装接口已转入 `../GripContact15/` 制作，继续工作以该目录可编辑源和导入记录为准；运行资产仍复用本目录对应的 UE 路径。

## 制作范围

沿用已接受的 lowpoly PKM 和 Feed13 弹链动画，为当前枪匠目录制作 PKM 专用配件。用户明确排除弹匣、加长弹匣与弹鼓，继续使用 PKM 原有弹箱和弹链。

- 瞄具：全息、全景红点、2 倍棱镜、1–6 倍 LPVO（包含倍率环与随上盖运动的导轨）。
- 枪口：消音器、制退器、钛合金制退器、战术消音器。
- 下挂：垂直、斜握把、棱镜握把、止滑握把、战术垂直握把；与已有 PKM 脚架互斥。
- 枪托：镂空、核心、快拆性能、战术伸缩。
- 后握把：幻影、均衡、防滑稳定。
- 战术设备：激光、手电，保留共享启停逻辑和真实出光接口。

共 22 个可选配件、24 个静态模型（另含倍率环、瞄具导轨），以及带独立原装枪托／后握把／枪口材质分段的 PKM 骨骼模型。仅对应原装分段随替换件隐藏。

## 材质与来源

共享配件来源与原始作者／授权沿用既有工程记录，素材路径保存在 `authoring.json`；供体清单来自 `../../A762Meshy20260920/Accessories05/sources.json`。这是已有工程资产的适配，不产生新的素材授权。

金属涂层使用当前 PKM 的 QBZ191 风格配方，参考 `/Game/Weapons/PKMLowpoly20260922/Bipod07/Materials/M_PKM_QBZ_Body`。参数及制作方法见 `coating.json`、`bake_coating.py`。

- 各配件保留原有 UV0、结构法线、AO、标识、镜片与分划线。
- UV2 使用 5 cm 实际尺寸的涂层映射，避免不同配件纹理颗粒大小不一致。
- 保留聚合物、橡胶、钛色装饰和镜筒内部；已有区域遮罩的材质只更换涂层输入。
- 新接口使用独立钢材材质和微表面法线；UE 对该法线仅翻转一次绿色通道。
- UE 材质均为 PKM 专用变体，写回实际导入模型的材质槽。

## 握持与机械动作

四组握持族（vertical / canted / prism / angled）各包含 12 段动作，共 48 段。战术垂直握把复用垂直握持族。

制作来源为既有 AKM 同类握把的手指接触姿态与当前 PKM 动作。按 PKM 的下导轨和握把位置重新定位左手及整条左臂，保留 PKM 右手、上盖、弹箱和 Feed13 弹链动作。换弹时只在持握阶段混入握把姿态，操作弹箱／上盖期间保留原动作。

瞄具和导轨挂接 `PKM_Cover`，随换弹开盖；ADS 校准使用同一上盖坐标。枪托、握把和战术设备使用烘焙后的 PKM 根骨局部坐标，导出轴向和缩放与现有骨骼一致。

## 可编辑源与接入

- `PKM_Modular_Editable.blend`：完整模块化枪械。
- `PKM_<family>_Editable.blend`：四组完整握持动作。
- `SM_PKM_<key>.blend`：单件配件、接口、UV。
- `PKM_Coating_Editable.blend`：涂层烘焙源。
- `Exports/`、`Animations/`、`Textures/`：UE 导入源。
- `author_geometry.py`、`author_animations.py`、`bake_coating.py`：可重复制作脚本。
- `import_geometry.py`、`import_<family>.py`：通过工程 MCP 互斥桥执行的分批导入脚本；完成记录支持从已保存边界继续。
- `code_changes.json`：本阶段运行时代码与枪匠目录的修改范围。`integrate_code.py` 是本轮一次性迁移脚本，不应重复执行。

目标资产目录：`/Game/Weapons/PKMLowpoly20260922/Accessories14`。

## 当前交付状态

模型、材质贴图、48 段握持动画和源码接入已制作并导入 UE：24 个静态模型、1 个模块化骨骼模型、37 个专用材质变体及新接口材质已保存；四组动作均已保存。保存记录见 `geometry_import.json`、`animations_import.json`。2026-09-22 常规 `FPSGAMEEditor Win64 Development` 构建成功，记录见 `build.log`。

按用户规则，本轮不启动 PIE、不追加截图、预览渲染或运行验收。实际安装位置、手部接触、瞄准和换弹表现由用户在游戏中测试。
