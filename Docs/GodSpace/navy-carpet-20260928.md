# 主神空间深蓝短绒地毯 V2

后续用户已明确反馈“地毯是成功调整了”；该认可针对 V2。金属收边随后单独修订，保留本材质与地毯几何。当前公开/本机依赖边界见 [整理与发布](publication-20260928.md)。下方原制作记录不代表本次重新测试。

## 本次反馈与修正

用户反馈第一版仍像平滑色块。读取正式 `DayNight_Lighting` 关卡确认结构网格使用 `MI_GodSpaceNavyCarpet`，组件材质覆盖为空，位置为 (-2400,-1300,0)、单位缩放。第一版没有高度视差，纤维法线强度仅 0.28、细法线 0.10，并把颜色变化限制在 0.88–1.12；绑定正确并不意味着细节足够可见。

按 `ue5-debug-validation/references/dynamic-terrain-material-loading.md` 和 `ue5-pcg-building/references/dungeon-surface-authoring.md`，复用丘陵/地牢的共享坐标浅层 POM、RNM 细法线叠加、距离与屏幕纹素渐隐。高度通过现有 Carpet 01 法线做周期最小二乘积分重建，没有从颜色中的阴影伪造高度。它是近似高度场，不是原始扫描高度；配套宏观法线从同一高度求导，微观纤维继续使用库内法线。

V2 物理采样范围为 90 cm，高度范围 0.38 cm，主体法线强度 1.0、细法线 0.65；纤维颜色变化放宽为 0.64–1.42。保留深蓝包边和香槟色缝线。

## 制作范围

复用项目已有的 `SubstrateMaterials/Textures/02_Upholstery/Textiles/T_Carpet_01_BC/N/R`。这套素材的绒面比 Carpet 02 更柔和；本次没有下载 Fab 商品，也没有更改原素材库。

主通道、横向通道和高台的蓝色表面改用深蓝短绒效果，加入低对比纤维、宽而柔和的绒面高光、深蓝包边及细缝线。已有的大理石和香槟金边框保留。蓝色材质槽同时用于平台底部，因此通过世界高度和朝上法线遮罩，保留底部原有蓝灰石材外观。

## 资源与成本

- 新材质：`/Game/Props/GodSpaceLayout20260927/Materials/M_GodSpaceNavyCarpet`。
- 场景绑定实例：`/Game/Props/GodSpaceLayout20260927/Materials/MI_GodSpaceNavyCarpet`。
- 使用库内颜色/细法线副本和新制 `T_GodSpaceCarpetRelief_N/HAR`，最大尺寸 2048，保留纹理流送和 mip。旧粗糙度副本留存，V2 不再使用。
- 共 4 张运行纹理。POM 上限 8 次粗步进加 2 次细化；近景最多 14 次读取，远景 3 次。视差在 2.2–6.5 m 渐隐，细纤维在 1.8–5.5 m 渐隐，并受屏幕纹素/掠射角约束；分支位于读取之前，远处跳过步进和细法线读取。
- 蓝色槽位采用 90 cm/UV 的流送密度，按主体高度与颜色的物理采样尺度提供请求依据，避免依赖整个通道的原始 UV 尺度；更细的法线层也使用这份保守请求，不扩大项目纹理池、不关闭流送。这是请求依据修正，未采集运行时 resident mip。
- Cloth 绒面着色，无新增三角形、材质槽、透明毛发层、顶点位移或模拟；POM 不改变轮廓和碰撞。
- `SM_GodSpaceStructure` 仅替换 `Blue grey stone inlay` 材质槽，碰撞和布局不变；不加载或保存地图。
- 不涉及已隐藏的下方云海、海面、天空和光照。

参数可在材质实例调整：`NavyPileColor`、`PileTileCm`、`PileReliefDepthCm`、`PileNormalStrength`、`FineNormalStrength`、`PileFuzzColor`、`PileFuzzAmount`。高度遮罩与边界定位对应当前主神空间布局，移动或重做布局时需同步调整生成脚本；改变物理采样尺度时，也需同步配套法线和流送密度。

## 执行记录

构建脚本：`SourceAssets/GodSpaceLayout20260927/Integration/build_navy_carpet.py`。高度制作脚本为 `author_carpet_relief.py`，着色源码为 `carpet_relief.ush`。原有 `import_assets.py` 也调用此制作与密度配置步骤，后续重导布局会继续绑定新材质。

V2 材质与贴图已通过后台 D3D12 commandlet 编译并保存；构建日志为 `Integration/Receipts/navy-carpet-relief-v2-build-02-engine.log`。该次执行停在后续网格 UV 数据设置，随后通过 `finish_carpet_relief_binding.py` 单独续接完成绑定与网格保存，退出码 0，日志为 `navy-carpet-relief-v2-binding-02-engine.log`。完整保存回执 `complete=true`、`revision=relief-v2`。主材质、实例、配套纹理与正式结构网格均已落盘。

原蓝色槽流送密度为 `[5343.974,199.971,24876.545,0]`，本次按 90 cm 世界投影设置覆盖值。这不是运行时低 mip 的实测证据，不能据此把上一版平滑观感归因于流送。

保存回执为 `Integration/Receipts/navy-carpet-saved.json`。执行前已备份旧资源与历史回执，路径记录在回执中；下方云海与海面保持本轮开始时的状态。

按用户规则，不启动或重启编辑器，不运行游戏、截图、渲染或额外验收。这里的成本是材质设计约束，没有实测帧率结论；最终视觉效果由用户在游戏中测试。
