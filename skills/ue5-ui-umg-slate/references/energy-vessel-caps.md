# 浮动能量条的端帽与魔法粒子

适用于已有玻璃容器式能量 HUD 的端部补全，不重新设计整条进度逻辑。保持原位置、尺寸、填充等级和显示参数；优先修改现有单个 UI 材质的采样和解析粒子。

- 从实际纹理布局读取上、下边界与底端尖点，按容器中轴做反射。顶部采样下端时使用 `sourceY=topBoundary+bottomBoundary-y`，新顶尖为 `topBoundary+bottomBoundary-bottomTip`。不要靠目测画第二个形状造成上下比例不同。
- 顶部遮罩、玻璃和填充纹理同步反射。反射区域的纹理梯度也要翻转 Y；使用显式 `SampleGrad` 避免区域边界的导数跳变引起 mip 接缝。正文液面仍用原始坐标，端帽按接近满能时的独立范围渐亮。
- 移除菱形／龙形装饰时，同时替换其遮挡或独立顶章逻辑，防止旧元素从共享纹理重新露出。环绕光点、轻雾、缓慢上浮拖尾沿用既有蓝色与亮度层次；粒子数量有固定预算，不随累计命中无限增长。
- 保留版本间真实依赖：符文 V3 制作脚本仍读取 PassiveV1 的 V2 HLSL、HudMotesV2 安装脚本及苍龙 HudV10 布局/纹理，不能因版本旧而归档这些输入。已替换的 Before 快照与重复导入宿主可按精确清单移入 trash。

符文战锤案例入口：`RuneboundHammerTuning.h::Hud` 指向 `HudSymmetricCapsV3/M_RuneboundEnergyHud`，通过既有 `UAzureDragonEnergyComponent` 配置材质。作者源 `SourceAssets/RuneboundWarhammer20261022/HudSymmetricCapsV3`，说明 `Docs/UI/runebound-hud-symmetric-caps-20261023.md`。材质保存、引用和后台加载成功与游戏画面验收分别记录；制作或沉淀技能不自动授权截图、渲染或游戏测试。
