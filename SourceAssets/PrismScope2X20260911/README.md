# 紧凑型二倍棱镜瞄具

最新运行版本见 [MachinedControls/README.md](MachinedControls/README.md)：顶部及侧面旋钮规则机械重建，保留上一轮扩大通视区的调整。

前一版 OpticalRefinement 已被 MachinedControls 替代，移入本机 trash/optic-workflow-20260911，源与散列见 Docs/Weapons/optic-archive-20260911.json。以下仅保留初版来源与历史验收记录。

游戏入口：M4A1 → 装备改造 → 瞄具 → 紧凑型二倍棱镜瞄具 → 应用并保存。

## 参考与来源

结构参考 Primary Arms GLx 2X 的短镜筒、目镜调节环和棱镜座布局：
https://primaryarmsoptics.com/optics/prism-scopes/primary-arms-glx-2x-prism-scope/

本资产为无品牌的游戏变体，没有下载或复用厂商模型、商标或产品贴图。三视图与建模参考由本会话内置 imagegen 生成，见 `three_views.png` 和 `reference_white.png`；不是原厂精确复刻。

## 生成与整理

先生成三视图，再生成同设计的单张浅灰三分之四参考图，交给 RTX 5080 上的 TRELLIS.2-4B。这里是单视图建模，三视图用于设计校对，不是多视图融合。

- 服务：192.168.3.142:8188，设备和队列快照见 system_stats_before.json / queue_before.json。
- Prompt ID：f2b590bb-0e4d-4d25-a317-f55d6f55e9fe。
- 1024_cascade，structure/shape/texture 步数 16/32/24，seed 91162，2K 纹理，目标 100K 面；实际任务约 177.241 秒。
- 完整请求及回执：generate_workflow.json / generate_receipt.json / generate_history.json。
- 原始文件及 SHA256：download_manifest.json；生成整理母版 96,513 三角面。

生成体的镜筒表面起伏与实心镜片不适合直接接入。保留母版的目镜纹路及调节件，重建规则镜筒、中央壳体、贯通光路、25 mm 窄夹座和螺钉。去除生成的实心镜片残面，增加独立低透明度镀膜玻璃和中心十字红点，再烘焙材质。调节件和目镜纹路仍保留生成模型的较软细节。

最终 21,604 三角面，较 96,513 面母版减少约 77.6%；3 个材质槽，4 张 2048² 贴图（BaseColor / Roughness / Metallic / Normal）。主体没有边界或退化面；装饰壳体有 13 条非流形连接边，未宣称为可打印的流形实体。两个玻璃面是刻意保留的双面薄片。本资产作为无碰撞的枪械显示配件使用。

可编辑文件：PrismScope2X_Editable.blend。导出：SM_PrismScope2X.fbx。可重复构建脚本：build_model.py（含不透明主体光轴射线断言）。单位为 cm：总长约 12.98 cm，底座宽 2.5 cm，光轴高度 4 cm。

## UE 接入与放大方式

资产目录 `/Game/Weapons/PrismScope2X`；配件 ID `prism_scope_2x`，M4 支持。改造目录、草稿预览、应用保存、装备恢复、未装备武器预览、库存图标和掉落武器均走现有通用接入路径。

固定二倍使用现有相机 FOV 系统，相对一倍 ADS 的 55° 垂直视场，采用 `2 * atan(tan(FOV / 2) / 2)`，同步鼠标灵敏度和改造预览。实机水平 FOV 49.66244°（16:9），角尺寸放大比 2.00000。它是整个瞄准画面放大，不是独立镜内画中画渲染。

校准目镜瞄准点 (-6.15, 0, 4) cm，沿用折叠机械瞄具、开镜动画和装配合同，不改变开镜耗时。模型做专用低透明度玻璃材质，避免实心遮挡。

## 验收记录

`build_native.log` 为原生代码构建记录；`import_report.json` 与 `SCOPE2X_IMPORT_PASS` 为资产导入证明。导入命令进程存在项目原有的 GameFeatureData 配置及 HTTP 8000 端口错误，退出码不是零，不能把命令退出码当成成功；导入断言、已保存资产及后续独立游戏进程共同验证结果。

`scope2x-first` 为首轮行为回归，59 + 55 项通过，但截图发现镜内被残留几何遮挡，因此不作为最终视觉验收。修复后重新运行 `scope2x-final`；最终日志、截图及数值汇总见 acceptance.json。截图中部分文件名沿用通用枪匠审计的 panoramic/holographic 名称，实际内容由 PrismScope2XAudit 标志选择本配件。
