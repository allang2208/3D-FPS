# M09 V22：主体及封口材质绑定修复

用户在 V21 排查确认后授权修复。本轮实际补绑并保存 `/Game/Monsters/HangingBellM09/V04/SK_M09` 的两个空材质槽：

- 索引 4，`M09_Body_SourcePBR_001` → 原 `M_M09_Body`。
- 索引 5，`M09_Closure_SourcePBR_001` → 原 `M_M09_Body`。

保存仅修改网格材质槽及修订元数据。保留其他槽、原 PBR 贴图、几何、UV、蒙皮权重、骨架、物理及当前 V18 抓击和 V20 转身速度。无需 C++ 构建或重新导入几何。

制作链同步修正：

1. `Tools/HangingBellM09/import_claw_continuity_v16.py` 优先保留已有非空精确槽名绑定；针对实际出现的 Body/Closure `_001` 名称，空引用时从原槽恢复材质。
2. `Tools/HangingBellM09/finish_arm_continuity_v16.py` 在载入主体之前保留当前文件的原 Body/Closure 材质引用，复制主体网格后复用这些材质，避免再次产生独立 `.001` 材质槽。

本轮未重跑 V16 整套几何和动画导入，因此不会覆盖后续的抓击修订。旧 Blender 制作文件保留不重存；已修正其生成脚本及既有导出对应的导入映射。

执行入口：`Tools/HangingBellM09/fix_surface_bindings_v22.py` 与后台入口 `fix_surface_bindings_headless_v22.py`。
备份：`SourceAssets/HangingBellM09Meshy20261003/SurfaceBindingV22/Before/`，含修复前正式 SK_M09 及两份原制作脚本。
保存收据：同目录 `Records/saved.json`，complete=true，changed_slots=4、5，正式网格已保存。

2026-10-04 15:48（北京时间）后台保存完成，commandlet 正常退出（0）。未启动 UE 图形编辑器、游戏、渲染或追加验收；视觉效果由用户体验确认。
