# Meshy 共振握把接入

用户选择的源：Selected_Meshy_Source.fbx，原路径和 SHA256 见 source.json。

## 完成内容

- 112466 三角面原网格用于 M4、AKM、QBZ191，各枪独立适配现有前握把安装框架。保持顶点法线，不重新减面、平滑或局部推拉网格。
- 以旧配件顶部安装条区域对齐，并按原抓握范围确定尺寸。根据现有 M4 idle 变形手套表面选择整体 X/Y 各最多1mm的位置微调；本次三枪结果均为局部X+1mm、Y-1mm，Z不变。AKM/QBZ的接触取样来自已适配范围映射，未逐枪重新制作动画。
- 保留 angled_foregrip 的身份、数值、所有抓握和换弹动画。没有改动骨骼轨道。
- 源文件无UV：新增SurfaceUV与ReceiverCoatUV，两者一致以匹配切线基准。金属/聚合物区域参考之前各枪已拟合版本转移；各枪金属沿用其机匣材质来源，聚合物保持独立微表面。材质非Meshy原始贴图。
- 每枪可编辑blend、FBX及GLB位于对应子目录。author.py、finish_blender.py、import_assets.py为制作入口。
- 已导入 /Game/Weapons/ResonanceGrip20260913/MeshyIntegration/{M4,AKM,QBZ191}/SM_ResonanceGrip；运行入口 M4AngledForegrip.cpp、AKMAttachmentVisual.h、QBZ191Attachments.h 已切换，修改前精确文件保存在Before。
- 使用内容导入宿主避开主工程此前AutoFootstep启动冲突；未改主工程插件设置。

## 交付边界

未进行本轮游戏/动画测试，未生成本轮接入验收渲染。现有动画已保留，但整体毫米调整及基线映射不等于所有动作零穿模；请用户重启编辑器后测试装备、ADS、换弹回握和材质观感。

源网格仍有先前检查中可见的内框折面，本次接入没有宣称修复它们。用户源FBX未修改。原有资产保留。
