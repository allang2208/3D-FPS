# 符文战锤能量HUD V3：上下对称玻璃封头

顶部以现有底部的玻璃尖拱、包边和封口结构作等比例纵向镜像，原独立圆环与硬连接线替换为完整玻璃封头。保留蓝色流光、符文螺旋带、10个聚集光点与22个上浮光点，不新增漂浮菱形、中心宝石或龙形装饰。

直接使用原有Empty／Full／Mask纹理，通过HLSL取样坐标镜像，不改写苍龙共用纹理、不生成替代底图。镜像中轴Y=1031.86611797，顶尖Y=71.91879287，底尖Y=1991.81344307；完整值记录在 `cap_layout.json`。顶部接近满能量时随之亮起，原九段液面映射、苏醒时长与脉冲参数不变。

单个Slate UI材质四边形、屏幕比例、左侧位置、透明度、显隐和32个解析光点保持既有合同。上封头的纹理显式采样梯度保持接缝附近的纹理密度；没有增加屏幕捕获、动态贴图或HUD面板。

制作入口：`prepare_caps.py` 输出本目录独立HLSL、布局和材质作者脚本；`author_isolated.py` 在私有后台工程保存新包，只安装新路径。`activate.py` 仅修改 `RuneboundHammerTuning.h` 的专用Hud路径，保留头部改造与其他常量。`build.ps1` 等待既有构建自然结束后执行必要Game／Editor目标；`record_delivery.py` 记录实际保存、安装及构建结果。

新材质为 `/Game/Weapons/RuneboundWarhammer20261022/HudSymmetricCapsV3/M_RuneboundEnergyHud`。实际完成状态以本目录 `import_receipt.json`、`build_receipt.json` 与 `delivery_receipt.json` 为准。没有打开UE界面、启动游戏、运行PIE、截图或验收渲染；视觉效果由用户实测。
