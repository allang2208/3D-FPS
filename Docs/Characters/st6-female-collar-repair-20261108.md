# ST6 女性领口贴合修复（2026-11-08）

本轮处理用户反馈的 Kaitlin 女性角色 ST6 战术上衣领口覆盖与穿模。保留原生身体材质、原袖、下摆及现有裤腰配对，只重建独立领口组件。男性、武器手袖、装备属性、图标和掉落模型不变。

## 制作依据与修改

女性旧派生器使用男女身体表面位移场适配领口，未读取独立头部的颈部皮肤；保存阶段又将 ST6 原专用领口 LOD 改为公共服装 LOD。本轮直接捕获当前 `SKM_MHC_Kaitlin_FaceMesh` 与 `SK_Kaitlin_Base`，在女性真实颈肩表面上重建覆盖，并保留原女性开口高度 144.067 cm。

- 领口外层依据真实头部表面生成，局部余量约 1.91–3.31 mm，前喉保留较大活动余量。
- 开口有真实端面与约 7.53 mm 内折边，内壁沿女性颈部表面制作；与外缘共享蒙皮权重。
- 胸肩连接处向身体原生权重平滑过渡，向衣身搭接约 6.53 mm。未隐藏整段脖子或身体，未新增整套躯干壳。
- 原袖和腰部饰边从原 DynamicMesh 保留，保留其材质槽、UV、骨骼和权重；新领口继续使用原 ST6 织物材质。
- 单独的 `DA_Kaitlin_ST6_NeckLODPolicy` 在三档 LOD 保留领口几何及绑定，避免距离切换重新削开颈部覆盖。

以上尺寸来自本次女性身体和既有开口，不是其他体型的通用数值。作者领口含 1,497 顶点、2,776 三角面；保存时 UV 接缝可拆分顶点。

## 已保存与接入

新资产目录：`/Game/Characters/ModularOutfit20260924/ST6FemaleCollar20261108/`。

保存 18 份网格：世界／本人身体各一份无裤原形、七类裤装配对及通用回退。`modular_outfits.json.body_variants.kaitlin.items.ue_st6_sleeves` 中共 70 个网格引用叶字段已切换，包含实际裤网格优先路由；原资产保留。

- 制作输入和旧配置：`SourceAssets/ST6FemaleCollar20261108/Inputs/`。
- 原生几何源：`SourceAssets/ST6FemaleCollar20261108/collar.json`。
- 路由及源散列：`manifest.json`。
- 实际网格保存回执：`saved_assets.json`。
- 本地配置接入及前后快照：`published.json`、`Publication/`。
- 生产工具：`Tools/ST6FemaleCollar/`。

`Tools/KaitlinPlayer/save_world_garments.py` 已接入 `apply.py` 的女性 ST6 领口及专用 LOD 配方，后续同身体的服装／裤腰派生使用该真实领口。`publish.py` 复用旧派生回执时也保留本次已发布的领口映射。女性头部或身体母版变化时，应重新捕获并制作此领口，不能继续沿用旧制作输入。

## 背包配对

依照服装技能，在衣物保存及发布后运行：

```powershell
$env:BACKPACK_FIT_RIG='Kaitlin'
$env:BACKPACK_FIT_SHIRT='ue_st6_sleeves'
& D:/FPS3D/FPSGAME/Tools/BackpackFit/run.ps1 -Revision ST6FemaleCollar20261108
```

`pending.py` 增加可选的身体／上衣范围，默认行为不变。本轮仅选择七款背包的女性 ST6 配对，保留男体作为既有坐标换算的参考输入，其他上衣及男性配对不重制。

七款配对均已完成：保存 7 份骨骼网格、3 份配套静态包体，按字段事务更新 47 个配置字段，并登记制作依赖。实际保存与接入回执为 `SourceAssets/BackpackFit20261024/ST6FemaleCollar20261108/saved_assets.json` 和 `published.json`；未运行背包动作或联机测试。

## 执行与验收边界

未主动打开或重启 UE；开始时已有编辑器及 PIE。普通结束 PIE 请求未解除保存限制，随后经已有 MCP StopPIE 接口结束会话。保存窗口期间现场编辑器退出并重新出现；保留现场，通过新的现有编辑器节点保存 18 份资源，没有关闭或强杀编辑器。原生 C++ 未变，不需要重新构建游戏模块。

本轮未运行游戏、动作、联机测试、截图或验收渲染。资产落盘与配置接入不代表所有动作下已通过无穿模验收，由用户实机测试。
