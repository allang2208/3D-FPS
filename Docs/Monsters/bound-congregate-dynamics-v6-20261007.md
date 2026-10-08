# 缚群：触手移动惯性与根部衣物 V6

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

用户反馈红圈处绿布和粗触手根部跟随错误、整条触手移动僵硬。按 `ue5-monster-workflow` 的 WitchRebuilt 连续布料及 M07 V38 固定边界方法制作。保留 V4 焊接连续肉体、UV、材质和 V5 三倍非线性出手，不改变伤害、缠绕及拖拽合同。

## 原因与制作

- 右侧绿布 `BC_RightLining` 顶部源权重主要来自 `leg_R3_upper`，与它覆盖的肩部／触手根部不对应。原导入曾统一移除衣物的攻击链权重，后续根部修改没有同步衣物。
- 57 骨攻击链创建于旧移动动作之后；原攻击控制在非攻击状态退出，没有移动惯性。V6 在脚部支撑和攻击控制之间加入专用二次运动节点。
- 在连续右侧布料代理上，把上段重新投射到实际躯干／近端触手支撑表面，插值表面权重，并沿布料邻接图平滑到原下摆。555 个代理顶点重新绑定；显示与代理使用相同权重、固定边界、活动范围。
- 上缘固定带与沿表面距离释放的下摆；1491 个代理顶点、50 个固定顶点；自由距离上限 12 cm，贴腿下缘收至 4.5 cm。显示面增加 4 mm 外向厚度及封边，2982 个显示顶点；附着带按 2.8 cm 制作间隙重新贴合。数值是制作参数，不是动态碰撞验收结果。
- 布料采用 `UWitchRebuiltClothingAsset` 的有界映射；右侧布料使用三个内缩的近端触手胶囊、背面接触约束、CCD 和稀疏自碰撞球。保留自由边的 Chaos 模拟，降低右侧动画牵引至 0.012，增加到两次子步。
- 触手二次运动采用耦合阻尼弹簧；从实际世界坐标目标的加速度产生移动与转身惯性。固定根部三段，沿长链逐渐释放，最大积分步长 1/120 s；近端弯曲小、末端弹性更明显。长度保持、平行运输旋转；跨动作快照不重复叠加二次运动。蓄力前 0.24 s 淡出，收势最后 30% 淡入；死亡停用并沿用原尸体方案。没有新增独立 Tick 或射线。

## 文件和落盘状态

- 源模型：`SourceAssets/BoundCongregateMeshy20261006/TentacleDynamicsV6/BoundCongregate_DynamicsV6.blend`
- 交换文件：同目录 `SK_BoundCongregate_DynamicsV6.fbx`
- 生产脚本：`Tools/BoundCongregate/author_dynamics_v6.py`、`import_dynamics_v6.py`、`finish_dynamics_v6.ps1`
- 接入目标：`/Game/Monsters/BoundCongregate/DynamicsV6/SK_BoundCongregate_DynamicsV6`，对应新版连续尸体，并保存现有 `BP_BoundCongregate` 的网格引用。
- `FPSGAMEEditor` 与 `FPSGAME` Development 已后台构建成功；`TentacleDynamicsV6/delivery.json` 已记录 `saved: true`，新版模型、布料、物理资产、对应尸体及原 `BP_BoundCongregate` 引用均已保存。
- 第一次沿用 V5 仅保存参数的 `-NullRHI` 启动方式在 FBX 构建期间中断，未形成保存回执。已换回 V4 模型导入的 `-AllowCommandletRendering` 后台生产方式，完整执行导入并得到成功保存回执。该参数用于资产构建，不启动游戏或产生验收渲染。

本轮不运行游戏、测试、预览渲染或截图。用户自行体验移动、转身、停步及攻击效果；不得把制作完成或包保存称为视觉验收通过。
