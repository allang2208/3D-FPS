# 战术垂直握把候选（2026-09-19）

**后续用户已授权游戏接入并指定开镜耗时 −25%。正式四枪版本、装配入口、材质与渲染见 [游戏接入说明](Integration/README.md)。下文记录最初候选制作阶段。**

按用户截图和配件标准工作流制作。范围为独立模型、材质、可编辑源与 UE 候选导入；当前游戏里的握把、枪匠条目、属性及抓握动画保持原引用。

## 来源与制作

- 原图：`Reference/user_reference.png`。
- 三视图：`Reference/three_views.png`，提示词保存在 `Reference/reference_prompt.txt`。左、右为相对的宽侧，第三幅为窄的防滑面；不可见区域为候选设计补全。
- 用户在 5080 显存不足、生成停留于第一步后，明确选择本机 Blender/Vibe3D 路线。本次交付的网格由本机 Blender 5.1.2 建模，未使用远程生成网格。
- 主体、收颈、侧面凹区和防滑纹采用连续网格；顶部安装座和装饰螺钉保留为可编辑分件。高模 108,960 三角面，导出游戏网格 27,998 三角面。
- 游戏网格单独展开 UV，从高模烘焙三张 2048 × 2048 贴图：BaseColor、MetalRough（G = Roughness、B = Metallic、R = 白色未使用）和切线 Normal。未烘焙 AO。法线源为 OpenGL 约定，UE 导入时翻转绿色通道。
- 聚合物细颗粒和暗色金属材质已转为游戏用贴图。可编辑文件保留隐藏高模并打包参考图与贴图。
- 尺度参考项目现有紧凑垂直握把，候选总高 10.35 cm；不是实物测量或制造尺寸。原点在顶部安装基准，主体沿 -Z，+X 为前方。

## 交付文件

- `Source/TacticalVerticalForegrip_Construction.blend`：分件、程序材质与连续主体的制作源文件。
- `Source/TacticalVerticalForegrip_Editable.blend`：高模、游戏网格、UV 和打包贴图。
- `Export/SM_TacticalVerticalForegrip_Candidate.fbx`：UE 静态网格导出。
- `Export/TacticalVerticalForegrip_Candidate.glb`：含材质的交换文件。
- `Export/Textures/`：三张 2K PBR 贴图。

UE 候选路径：`/Game/Weapons/Candidates/TacticalVerticalForegrip20260919/SM_TacticalVerticalForegrip_Candidate`。

## 制作入口

1. 在独立 Blender 后台进程执行 `Scripts/build_local.py`，建立可编辑分件源文件。
2. 执行 `Scripts/bake_local.py`，制作游戏网格、UV、烘焙贴图并导出。
3. 通过本机项目桥 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript <本任务>/Scripts/import_candidate.py` 在当前打开的 UE 编辑器内导入并保存候选；该脚本拒绝覆盖已存在的候选路径，不应直接重复运行。
4. 经现有 MCP 桥顺序执行 `Scripts/vibe_lods.json`、`Scripts/vibe_collision.json`，保存三个 LOD（1.0 / 0.5 / 0.2）和最多两个凸包的简单碰撞。

早期远程生成脚本、被中止的生成任务回执以及旧目录数据备份已移到项目根目录 `trash/attachments-grip-drum-20260920/SourceAssets/TacticalVerticalForegrip20260919/`。未使用远程模型产物；本机建模母版和正式四枪源文件保留。

## 交付状态

本机建模、PBR 烘焙、FBX/GLB 导出与 UE 候选导入已完成。UE 返回网格、材质与贴图保存成功；Vibe3D 返回三个 LOD 和凸包碰撞创建成功。制作结果记录于 `authoring_receipt.json`、`import_receipt.json` 和 `vibe_receipt.json`。编辑器全程保持打开。

未替换正式握把或接入枪匠、属性、挂点和手部动画。未进行检查、测试、游戏运行、截图或成品预览渲染，接口返回不代表视觉或游戏验收通过，交由用户测试。用户提供的截图许可未明确，本轮不公开发布其衍生源文件。
