# 符文战锤能量条：上下对称封头

顶部沿用底部的玻璃尖拱、外包边与横向封口，按现有玻璃柱中点作等比例纵向镜像。原顶部独立圆环和硬连接线移除，保留蓝色魔法流光、符文螺旋带以及32个解析漂浮光点。

原始贴图坐标的柱顶为422.522908px、柱底封口为1641.209328px，中轴Y=1031.866118px；底尖Y=1991.813443px对应新顶尖Y=71.918793px。顶部直接采样原底部的Empty／Full／Mask图层，避免重新生成时丢失玻璃纹理和包边细节。显式采样梯度使接缝两侧保持原纹理密度。

充能仍使用既有九段液面映射，顶部封头随接近满能量亮起，苏醒沿原Pulse／Burst闪亮。32个光点与柔和光雾继续漂浮，顶部没有新增菱形、宝石或龙形装饰。

## 界面与生命周期

沿用 `UAzureDragonEnergyComponent` 与 `SAzureDragonEnergyHud` 的单张UI材质四边形。能量来自符文战锤原充能状态，原Fill／Age／Reveal更新方式、无命中测试输入、分辨率缩放、左侧定位和卸下隐藏逻辑均保留，不新增面板或输入占用。此次仅修改符文战锤专用材质路径，不改苍龙共用资源或战斗数值。

## 制作与接入

作者源为 `SourceAssets/RuneboundWarhammer20261022/HudSymmetricCapsV3/`。`prepare_caps.py` 保存新HLSL和精确镜像布局，`author_isolated.py` 在私有无界面工程创建并保存新材质包；只安装新路径，不覆盖已有材质。运行入口为 `RuneboundHammerTuning.h` 的Hud常量，必要Game／Editor构建写入同目录回执。

是否已经导入、构建和接入以 `import_receipt.json`、`build_receipt.json`、`delivery_receipt.json` 为准。本次不启动UE界面、游戏、PIE或验收渲染，实际视觉效果由用户测试。
