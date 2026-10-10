# 原厂白水晶抛光晶面 V41

用户否定 V40 磨损观感后，选择先做“清晰晶面＋有层次的反射”的抛光石英方向。本版从磨损前 V36 作者源出发，保留 V35 造型、晶面法线、0.35 mm 倒角及现有 V36 透光参数。只修改原厂白水晶世界和预览材质。

## 制作内容

- 去掉 V40 磨砂、划痕和蚀点，也去掉 V35 微表面贴图对当前着色的扰动。新材质不采样这些四张表面贴图；旧资产保留历史。
- 大晶面使用原有平面法线，窄倒角使用原有平滑法线。切线空间 Normal 固定为 `(0,0,1)`，不额外平滑几何，不制造内部反射面或不透明外壳。
- 现有顶点红通道区分晶面，映射粗糙度 0.05–0.085；绿通道选择窄倒角，粗糙度 0.055。变化按整片晶面分布，替代 V40 随机斑块。保留介电 IOR 1.544 及由其计算的 F0，没有金属化或人为发光高光。
- 世界材质启用 `screen_space_reflections`，维持 Surface Forward Shading，并启用天空 Cubemap 过渡混合。实际反射仍来自当前场景；画外物体和遮挡处受 SSR 本身限制。
- 背包／改造台是间歇式捕获，预览不启用依赖上一帧的 SSR，继续使用当前工作室环境图与照明。世界和 UI 共用晶面、倒角及透光配方，UI 保留独立覆盖率适配。
- 本机 UE 5.8 的 `ForwardLightingCommon.ush` 在延迟渲染的表面透明路径已支持混合反射捕获。材质允许参加现有 Front Layer Translucency；本轮没有更改项目或后处理的 Lumen 高质量透明反射开关，不能把本次交付描述成已开启全局高质量反射。
- 保留原有限光程吸收、消光系数、介质散射、根部参数、关闭折射的设置，以及 `StaffLightAmount` / V32 曝光分支。几何、G 键照明、其他元素杖头、杖冠、符文和玩法均不改。
- 不增加贴图、光源、Tick 或 C++；表面采样减少，但 SSR 的实际 GPU 代价未经采样，不宣称性能提升。

## 制作源和重导

作者目录：`SourceAssets/ApprenticeStaff20260927/QuartzPolishV41`。

- `author_polish.py` / `Staff_QuartzPolish_V41.blend`：从 `QuartzOpticsV36` 原作者源保存纯材质修订，无模型重导。
- `parameters.json` / `ue_material.py`：抛光晶面及世界／预览反射设置。`OpticalChord.hlsl` 沿用 V36 原光程。
- `install_ue.py` / `run_install.ps1`：保存两件独立候选和两件正式材质；已有 UE 时统一通过互斥桥接入。
- 正式世界路径：`/Game/Weapons/ApprenticeStaff20260927/QuartzAimV22/Materials/M_Staff_QuartzDenseV22`。
- 正式预览路径：`/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23`。
- V36 入口优先采用已完成且 active 的 V41，V22／V35 旧入口沿此链路。V40 已归档；当前重建不再读取或改写 V40 回执，旧入口也不再回退到磨损方案。
- V41 `Before/Content` 和 UE `/QuartzPolishV41/Before` 保存本次操作前的 V40 材质。若要恢复干净的 V36，应从 `trash/staff-runes-retired-20261010/SourceAssets/ApprenticeStaff20260927/QuartzWearV40/Before` 恢复备份，不能混淆两个恢复点。

## 状态

Blender 作者源已后台保存。沿用用户此前结束游玩以完成接入的授权，结束了现有 PIE 并保留编辑器；随后通过互斥桥完成两件独立候选和两件正式材质编译与保存。`install-receipt.json` 为 `complete=true, active=true`，返回 `STAFF_QUARTZ_V41_SAVED materials=4 wear_removed=true`。V40 回执已关闭 active，旧入口改为保留 V41。本轮未启动游戏、运行测试、截图或验收渲染，最终观感由用户确认。
