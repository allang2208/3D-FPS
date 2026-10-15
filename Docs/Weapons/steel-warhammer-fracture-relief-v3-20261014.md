# 战锤砸地裂纹 V3：破碎块面与凹陷贴花

用户截图否定 V2：等宽深黑直线、近乎均分的放射分支和缺少表面深度，使地裂看起来像画在地面的树枝图案。本轮仅替换地裂表面，保留烟尘、飞散碎石、冲击波、伤害、眩晕与动作。

## Fab 查找结果

- [Free Surface Decals - 5 PBR Decals for Unity & Unreal](https://www.fab.com/listings/823bc036-df2a-4f6f-a644-bab8eac213b4)：2026-10-14 读取的官方页面标为 Free；作者说明包含混凝土裂纹等五种贴花，提供 1024 像素颜色／透明度、法线、粗糙度和高度贴图，并提供 UE 5.8 版本。
- [Decal - Ground Cracks - Game Ready](https://www.fab.com/listings/b2ba37f1-2dee-4ccc-896c-87a44bfb17b9)：官方搜索结果标为 Free，描述为照片制作的裂纹贴花、4K PBR 图；本轮直接页面读取未成功。
- [Bomb Crack Ground Line (Free)](https://www.fab.com/listings/f90434f1-d3e0-4aa7-b0ce-3b924ad82035)：官方页面有免费标记和 FBX/PBR 爆裂效果描述，但读取内容为较旧页面快照。

上述仅为查找结果，没有领取许可、下载或导入第三方包，也没有将商店页面当成项目资产。用户允许直接优化，因此本次接入的是原创制作源，不依赖 Fab 登录或下载。

## 制作与运行

- 原创 Voronoi 破碎块面：中心密集小碎块、外围稀疏大裂片；主裂缝沿不规则块面边界形成连通路径，分叉、长度、宽度不再均分。
- 裂缝边缘加入细碎偏折、崩边和粒状变化，往外逐渐变窄。减少纯黑覆盖，保留接收地面的颜色，并缩小主要破坏区的视觉跨度。
- 从以厘米为单位的凹陷和倾斜碎片高度场生成 DirectX 法线，接入真正的贴花 Normal／Roughness，不把灰色描边当作凹凸。
- 三张 2048×2048 贴图：sRGB 颜色、线性法线、线性遮罩（R 覆盖，G 裂隙，B 粗糙度，A 源高度）。保留 mip 与流送、纹理边界 Clamp。运行材质为三个纹理采样，不再逐像素计算旧版放射线距离循环。
- 复用既有八槽池、地面法线投射、随机角度和 Age 时钟，3.3 秒开始淡出、5 秒结束。仍为临时视觉贴花，不破坏地形和碰撞；现有圆形伤害范围不受贴花缩小影响。

源：`SourceAssets/SteelWarhammer20261014/CrackReliefV3/`，包括生成器、原始厘米高度场、PBR 图、导入器及回执。运行资产目录 `/Game/Weapons/SteelWarhammer20261014/CrackReliefV3/`；唯一原生修改为 `WarhammerSlamFXSubsystem.cpp` 的裂纹材质引用。V2 留存为被否定的历史版本。

按用户规则执行后台制作、导入保存和必要正式编译；不主动运行游戏、截图、验收渲染或性能测试。实际资产保存与构建状态见本批回执，观感交由用户测试。

实际交付：三张 2K 贴图及 `M_WarhammerFractureRelief` 已导入保存，`import_receipt.json` 为 complete，第二次导入退出码 0。首次材质连线因 UE 当前输入引脚名称不叫 Coordinates 而中止，改为读取该节点的实际首输入名后完成；旧尝试日志保留。沿用户此前“残留进程直接关闭”的授权，确认并结束同一后台任务中停滞于退出阶段的 PID 111440，正式 Editor 构建随后成功，最终游戏模块 DLL 完成链接。回执见 `build_receipt.json`、`delivery.json` 和 `residual_exit_receipt.json`。没有本轮游戏或视觉验收记录。
