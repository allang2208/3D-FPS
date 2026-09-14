# 主场景地面遮挡胖子脓液：根因与修复

## 用户现场与定位

用户击杀胖子并暂停 PIE 后，读取了 `/Game/GameMaps/UEDPIE_0_DayNight_Lighting` 中的 `FatZombiePusPool_0`。现场随机种子为 `1584119041`，位置 `(-353.966559, 638.393534, 2.150003)`，Yaw `-87.827148`。

现场组件可见、主渲染通道开启；世界包围盒 Z 为 `0.35–1.45 cm`。编辑器随后正常退出，后续使用相同种子与坐标在编辑器世界还原，未启动 PIE 或推进战斗。

还原得到 1056 个三角面、3168 个顶点，1056 个面均绑定顶点颜色，Alpha 范围 `0–1`、平均 `0.788`。动态材质为 `MID_MI_FatZombie_Pus`，Visibility=1。材质使用 Masked，Alpha Threshold 连线正确。地面简单/复杂碰撞面及原始静态网格顶点均位于 Z=0。

## 根因证据

主场景 `Floor` 使用引擎 Cube，缩放约 `(5000, 5000, 0.4)`，相当于约 `5 km × 5 km × 40 cm` 的地面。针对用户明确反馈的显示故障进行了 BaseColor / SceneDepth 对照，不作为完整玩法验收：

- 原地面：脓液和普通不透明替代材质均被遮住；脓液额外抬高 2 cm 仍不可见，抬高 20 cm 才可见。
- 仅显示 Floor 与脓液，结果相同；排除了其他场景物体。Floor 没有 Nanite 数据；切换 Nanite 设置不改变结果。
- 顶视 SceneDepth 读数为 195 cm，相机 Z=200，显示地面深度相当于 Z≈5 cm，足以遮住原薄膜；静态网格顶点仍为 Z=0。
- 临时将 Floor 的 XY 缩放改为 100，保持碰撞面高度，原脓液立即显示。由此将故障定位到这个超大缩放地面的绘制深度偏差。未把某个未读取的 GPU 内部公式作为已证实根因。

证据：`Saved/Logs/FatZombie-reconstructed-ready.log`、`FatZombie-floor-vertices.log`、`FatZombie-isolated-floor.log`、`FatZombie-floor-scale.log`；图像位于 `Saved/FatZombiePusVisibility/`，`reported-material.png` 为遮挡状态，`floor-scale-100.png` 为缩放对照。

## 实际修改

- 新建 `/Game/GameMaps/Geometry/SM_MainGround_Subdivided`，把原地面尺寸直接写入网格，约百米网格单元，共 9796 个三角形。
- 保留原 Floor Actor、位置、旋转、约 5 km 覆盖范围、40 cm 厚度、格子材质和 BlockAll 配置；替换网格后使用单位缩放。简单碰撞仍为覆盖相同尺寸的单个盒体。
- 保存主场景 `Content/GameMaps/DayNight_Lighting.umap`。不修改共享的引擎 Cube。
- 本次未改脓液材质、随机轮廓、贴地高度、伤害及死亡动画/布娃娃时序。

制作脚本：`Tools/FatZombie/fix_main_ground_surface.py`。原场景备份：`Saved/FatZombiePusVisibility/ground_fix/DayNight_Lighting.before.umap`；来源与落盘记录为同目录 `source.json`、`applied.json`。备份仅用于本次地面修改恢复，不应覆盖此后其他任务的地图修改。

## 交付边界

保存并重新加载修复后的地图，在相同种子/坐标完成本故障的定点对照：`fixed-ground.png` 已显示完整脓液与周围液滴，组件高度仍为 `0.35–1.45 cm`。该图为 BaseColor 诊断图，不代表最终受光效果预览。

原生诊断工具按需通过 `fps.InspectFatZombiePus` 执行；默认只读取数据，限定主场景编辑器世界。`-FatPusDrawDiagnosis -FatPusFixedGround` 仅捕获当前地面；完整对照分支会恢复地面的临时变换。不会在正常游戏中自动执行。脚本入口为 `Tools/FatZombie/read_reconstructed_pus.py`。

命令行宿主仍有既存的 GameFeatureData Asset Manager 配置错误，导致相关进程退出码为 1；本次任务完成以制作保存标记、诊断数据和图像为证，未修改该无关配置。未进行新的游戏内击杀、踩踏伤害、布娃娃、寻路或消退回归，交由用户复测。
