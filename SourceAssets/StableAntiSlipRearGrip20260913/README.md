# 稳固防滑后握

用户参考：reference.png。三视图：three_views.png，内置 image_gen 生成。侧面未见区域为设计补全，不是精密工程图。

TRELLIS.2-4B 多视图 seed 91713，1024_cascade / SS64 / 16-32-24 steps / 4096 texture / 500000-face export target。generate.py 保留请求、历史和模型，仅下载，不启动渲染或游戏。裁切左宽侧 x0–600、中窄面 x600–930、右宽侧 x930–1536，高1024；映射到节点 front/left/back，以生成器的 front_axis=z 为基准，接入时再变换到枪根坐标。

配件 ID：stable_antislip_reargrip，reargrip 槽。用户数值：开镜速度 -10%（耗时 1/0.9 倍）、后坐力控制 +20%（recoil_mult 0.8）、枪械稳定性 +15%（shake_mult 0.85）。沿用现有配件百分比口径。

本轮不进行运行测试或验收渲染。候选、导入和实际游戏测试状态分别记录，不将生成母版当作完成接入。

## 本轮交付状态

已完成三视图、独立图标、TRELLIS.2 三视图母版生成（seed91713）、游戏网格与各枪原厂接面适配、M4/AKM/QBZ191 FBX 和可编辑 Blend、贴图材质导入、reargrip 目录数值与运行加载分支。Editor 独立后缀913538编译成功。

UE导入脚本成功并保存三枪资产，见 import_results.json；进程因已有 GameFeatureData 配置错误退出1，不表示导入脚本失败。未运行游戏、握持/接缝测试或验收渲染；模型拟合效果由用户实际体验。未修改手臂动画。

运行路径：/Game/Weapons/StableAntiSlipRearGrip/{M4,AKM,QBZ191}/SM_StableAntiSlipRearGrip。原配件保持独立；选择本配件才隐藏原厂后握把，拆卸恢复走既有入口。图标位于 Content/ColdSteelData/AttachmentIcons20260913/reargrip_stable_antislip_reargrip.png。

## 2026-09-13 用户选中重抽版

当前替换为 seed 91727；运行引用与三枪适配、材质规则见 Selected91727/README.md。上文 seed 91713 为历史版本。
