# 默认水晶表面 V35 第一轮候选

2026-10-03。用户授权按通透天然石英方向调整；本轮制作表面与透光，尚未获用户观感确认。

- 两个默认模型从实际安装 UE 网格导出，非水晶部分沿用；水晶增加 0.35 mm 两段棱边倒角。可编辑源：`Staff_QuartzSurface_V35.blend`；两个导出 FBX：`Export/`。
- 两张 512 纹理独立表达浅生长纹／微小蚀点。清透晶面粗糙度 0.06–0.12；表面纹理／棱边与根部透明信号各自控制。
- 世界／UI 各有独立候选材质，现用世界 `M_Staff_QuartzDenseV22` 与预览 `M_StaffQuartzPreviewV23` 同步重建保存。点灯参数、V32 曝光处理与 C++ 保留；本轮没有内部体积、折射或点灯强度改动。
- 候选导入完成后更新现用 `Meshes/`、`BarkRebuildV21/Meshes/` 的 `SM_Staff_Base` 和 `SM_Staff_head_crystal_false`；四个元素杖头继续用 V33。
- 原六个目标有 UE 内 `QuartzSurfaceV35/Before/` 副本，以及 `Before/Content/` 内部路径一致的磁盘副本。关闭 UE 后明确运行 `restore_offline.py` 可撤回；本轮没有执行回退。

`inputs-receipt.json`、`author-receipt.json`、`install-receipt.json` 均 complete。实际用 Blender 后台制作、D3D12 无界面 commandlet 导入／材质编译／包保存完成；没有启动交互编辑器或游戏、没有测试／截图／验收渲染。静态目录图未重新生成。完整范围见工程 `Docs/Weapons/staff-quartz-surface-20261003.md`。

当前重建参数为 `parameters.json`，配方为 `ue_material.py`。V22 旧材质入口在安装回执 complete 后委托新配方，V21 重导入口保留新默认模型；避免旧入口覆盖本轮候选。原 V21 Blend 作为历史源保留，新默认水晶几何编辑从本目录 Blend 开始。
