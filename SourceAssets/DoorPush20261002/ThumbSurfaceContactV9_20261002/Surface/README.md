# M16 左拇指局部表面 V9 作者源

当前制作只改近景拇指的表面响应，保留 V8 拳形、手腕、骨骼、UV 和蒙皮。

## 作者输入中的实际问题

`Tools/ModularOutfit/bake_original_shape_skin.py` 的甲片是统一偏粉色区，末端混合 48% 米白色，皮肤褶线的基色直接压暗 10%。这三者都被同一张 UV0 图烘焙后，握拳近景会露出甲片像贴片、甲缘与关节纹颜色黏在一起的情况。该脚本按三角面主导骨权重选择指部，对边界也缺少逐像素解剖分区，不能把它当成真实扫描细节。

V5 材质同时以 .55 强度把通用人体皮肤 COLOR 投射到拇指，而掌侧微法线减弱 60%。近景可能以色斑为主、浅表皮纹为辅。现有源并未证明 UV 损坏或 sRGB 设置错误：基色为 sRGB，法线和 mask 为线性；所以本版不修改坐标或归因成压缩错误。

## 本版制作

`author_thumb_surface.py` 读取 canonical M4 解剖数据，在既有 V5 HLSL 中增加有限的左拇指胶囊区。局部减轻涂黑的折纹、减弱通用人体肤色色斑、恢复适度的掌侧皮纹。拇指甲用下面的肤色与较浅的甲片色混合，保留窄游离缘，并增加很弱的纵向粗糙度变化。没有全局锐化，没有新贴图采样，没有 POM 循环或位移。

输出 `skin_surface_thumb_v9.hlsl` 的 Custom inputs/outputs 与 V5 完全相同。普通裸手 `M_BareFamily_Hands` 与基础视模 `M_BareNative_Default` 的既有 V7 软掌法线处理也一并保留，基础视模前臂区域继续由 ForearmMode 禁止使用手部烘焙法线。

## 接入要求

复制当前 M16 的 canonical-coordinate 材质／实例作为本版局部派生，将 MP_NORMAL 的 Custom code 替换为输出 HLSL，保留连接和参数。RestPosition 必须来自 canonical UV1.xy、UV2.r；RestNormal 来自 UV2.g、UV3.xy，不能换成原生 M16 的 PreSkinnedPosition。仅给 M16 当前裸手与伴随裸手区域的材质槽赋值，保持武器、衣物和手套材料，不修改共享 V7 父材质。

这是作者源交付，还没有导入 UE 或进行编译、渲染、游戏测试；实际导入及资产保存由根代理完成并记录。
