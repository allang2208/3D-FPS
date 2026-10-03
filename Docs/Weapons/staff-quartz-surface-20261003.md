# 默认杖头水晶 V35：第一轮表面与透光

用户授权按优化计划调整。先交付通透主体、清晰晶面高光与细小棱边的候选，内部视差／体积纹理、折射和点灯亮度留到用户确认这一轮基础质感后处理。本次没有默认测试、截图、游戏运行或验收渲染。

## 制作范围

- 从实际安装的 `Meshes/SM_Staff_Base` 与 `Meshes/SM_Staff_head_crystal_false` 导出冻结输入；保留其非水晶几何、材料绑定、厘米坐标与六槽接口。
- 在默认水晶上做 0.035 cm、两段的局部棱边倒角，保留原轮廓与晶面，不增加内部羽片、套壳或新主体造型。
- 单独制作两张 512 像素纹理：微小生长纹／浅蚀点切线法线，以及生长纹与浅蚀点遮罩。纹理由确定性的程序配方制作，未调用图片生成或效果渲染。
- 顶点色 R 为晶面粗糙度差异、G 为细小倒角区域，非水晶原顶点色保留。干净面粗糙度为 0.06–0.12；局部细纹、磨损与棱边分别追加，不再复用内部雾化噪声。
- 透光色清透区 `(0.95,0.965,0.958)`、根部雾化区 `(0.84,0.86,0.85)`；覆盖率以 0.22 为起点、掠射角和根部局部追加、上限 0.42。根部信号仅在晶体下方 8 cm 渐隐。当前仍为表面雾化近似，没有声称完成内部体积或物理厚度积分。
- 点灯继续使用原 `StaffLightAmount` 与 V32 曝光分支、相同运行强度；未修改 C++、G 键动作、技能或元素晶头。

## 源与接入

作者入口：`SourceAssets/ApprenticeStaff20260927/QuartzSurfaceV35/`。

1. `run_install.ps1 -Stage prepare`：若编辑器已运行则走现有互斥桥；否则等待已有构建／commandlet 后用无界面 D3D12 commandlet 保存六个 UE 回退包、保留原路径的磁盘包，并导出两件实际输入。
2. Blender 后台执行 `author_surface.py`：保存 `Staff_QuartzSurface_V35.blend`、两个 FBX、两张纹理与 `author-receipt.json`。
3. `run_install.ps1 -Stage install`：先导入并保存独立 V35 模型／世界材质／预览材质，再更新现用两个材质与四个 Base／原厂杖头网格。每个保存记录到 `install-receipt.json`。

世界材质继续用 `QuartzAimV22/Materials/M_Staff_QuartzDenseV22`，UI 用 `UI/GunsmithWorkbench/M_StaffQuartzPreviewV23`；世界保留 Thin Translucent，UI 保留 Default Lit / Before DOF 覆盖率合同，因此无需修改预览路径或构建 C++。默认装备、改造台、背包动态模型和掉落物通过现用资产路径获得本次调整；已有目录 PNG 未重新渲染。

`QuartzAimV22/ue_quartz_material.py` 在 V35 安装回执 complete 后委托新配方；`BarkRebuildV21/import_model.py` 同样保留 V35 默认两件导出物，四个元素晶头仍沿 V33。新的可编辑几何源为 V35 Blend，原 V21 Blend 保留作历史源。

## 回退与状态

独立候选与 `Before` 回退包保留。需要撤回时，关闭 UE 后明确运行 `restore_offline.py`，恢复六个原路径包并关闭 V35 配方委托。该脚本不自动执行、不关闭任何进程。

本轮 `prepare` 与 `install` 无界面 D3D12 commandlet 已执行完成、Blender 后台制作完成；`inputs-receipt.json`、`author-receipt.json`、`install-receipt.json` 均记录 complete。独立候选两个网格／两个材质、两张纹理，以及现用四个网格／两个材质已保存；六个原包有 UE 内副本与原路径磁盘副本。执行日志位于 V35 作者目录。

材质编译与包保存仅属于制作接入，不代表用户已认可观感；未启动游戏、未做测试或验收渲染。无需 C++ 构建。第二轮内部深度、适度折射与点灯表现待用户反馈。
