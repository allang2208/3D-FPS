# 突变体 3：近景贴图、法线与材质整理

当前版本与恢复顺序见 [突变体发布入口](Mutant3FeralPublication20260923.md)。本文保留阶段记录；其中 before/baseline 快照及已退役独立手臂求解已按归档清单移至 trash。

后续用户反馈：“成功了”。此为用户对组合修订的反馈，不是本轮新增运行或性能测试。

用户报告近距离脸部呈块状、皮肤和裤子纹理模糊；本次按已确认方案完成加载策略、法线与材质细节。运行时 Mip 驻留根因尚未采集，不将本次实现描述为已实测消除全部模糊。

## 已制作及保存

- 正式网格仍为 `/Game/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw`。
- 从已接受的 `Mutant3_OpenClaw_Source.blend` 导出显式法线。身体保留源自定义角点法线；671 个爪骨权重顶点按权重混合重新计算的平滑手指法线。没有编辑位置、UV、蒙皮权重或骨架；只导入网格，不导入或保存动画，不更新 Skeleton 参考姿态。
- UE 导入源法线、计算 MikkTSpace 切线，启用全精度 UV。材质槽仍为单槽，已有 section 0 修复逻辑继续保留；重建 UV 流送密度。
- 新实例 `/Game/Monsters/Mutant3Meshy/SurfacePolish/MI_Mutant3_SurfacePolish` 使用既有共享母材质 `M_InfectedSurface_V1`。不修改共享母材质或其他怪物实例。
- 复用该怪物已有 Style V1 烘焙颜色、DirectX 法线、ORM 和组织遮罩，另存四张专用纹理到 `SurfacePolish/Textures`。颜色和法线最大 2048，ORM/组织遮罩最大 1024；保持流送开启，非永久常驻。颜色轻度 Sharpen1，其余沿纹理组规则。法线已是 DirectX，不再翻绿通道。
- 粗糙度采用烘焙分区：皮肤约 0.57–0.69、布料约 0.76–0.90；法线强度 0.9，干表面 Specular 0.25，湿表面 0.34。只对本实例做轻微肤色和布料调整。

## 运行时加载

`Mutant3SurfaceStreaming.cpp` 在 BeginPlay 一次缓存本实例四个纹理参数。距离流送倍率为 1.5，不修改碰撞或模型包围盒。

每 0.75 秒检查本地玩家视点距离，12 m 内异步请求最高允许 Mip，期限 2 秒。远离或销毁后请求自动到期；不取消其他突变体对共享贴图的请求。多个突变体复用同一套纹理，不按 Actor 复制资源。专用服务器跳过，EndPlay 清理计时器。没有同步等待流送/着色器、每帧全场扫描或全局画质设置修改。

实际显示仍受贴图流送和整机显存情况影响；本次没有采样实际驻留分辨率、FPS 或显存占用。

## 重建与恢复

- 作者脚本：`SourceAssets/Mutant3SurfacePolish20260923/author_normals.py`。
- 保存脚本：同目录 `install_surface.py`；仅在编辑器关闭时通过后台 Python commandlet 执行。
- 来源与保存回执：同目录 `normal_authoring.json`、`installation.json`。
- 原源码、导出 FBX 和资产备份：同目录 `before_source/`、`before_content/`。
- 已同步 `claw_reference_20260923/author_open_claw.py` 的手指法线制作，以及 `import_open_claw.py` 的源法线导入、UV 精度和材质保留，避免后续重导覆盖优化。
- `RepairSurfaceBinding` 继续修复源 polygon/渲染 section，但保留当前材质，不再强制换回早期基础材质。
- 既有材质烘焙来源详见 `Docs/Monsters/MonsterStyleV1.md`；复用原库内 ZombiSkinMaterial 来源，无新增下载、付费生成或许可变更。

## 交付边界

常规编译及六个资产保存完成。模型轮廓精修及新增中远距 LOD 留待用户判断本轮效果；战斗、飞扑手势和动画文件没有改动。本次未启动编辑器、游戏或进行视觉/性能测试。

后台接口注意：UE 5.8 的 `SetMaterialInstanceTextureParameterValue` / `SetMaterialInstanceScalarParameterValue` 实现会赋值，但返回值始终为 false。首次导入因此在四张贴图保存后中断，续接时跳过已完成贴图，从材质实例阶段完成；不是贴图赋值被引擎拒绝。
