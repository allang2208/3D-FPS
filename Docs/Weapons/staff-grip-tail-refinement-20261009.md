# 法杖符文配色、握柄表面与尾饰摆动（2026-10-09）

用户要求三种符文按颜色区分、按 SKILL 材质要求强化握柄，并参考镇岳尾坠增加物理飘动。本轮不改法杖数值、手部动作、水晶与杖冠，不生成图标或启动验收。

## 制作内容

- 鹰眼：青绿；暴击：朱红；风暴：蓝紫。沿用已经接入的三张原始符文图、贴合树皮网格、浅刻边缘与错相呼吸。`RuneRefinement20261009/palette.json` 同时驱动 UE 制作配方和 Blender 源，避免重导恢复旧暖铜色。
- 四种握柄保留原网格、UV0、握持位置与槽引用。原木为轻蜡面，松木为浅色封闭木孔表面，檀木为深色细密油润表面，合金为裸露缎面加工金属及原有窄环边。三种木材共用独立木材母图，各自材质实例控制纹理尺度、孔隙微法线、粗糙度与颜色；合金使用独立母图及实例。
- 木材 Metallic=0，合金 Metallic=1；不把灰色金属值套到木材。原木表面的孔隙法线来自原有 `T_WoodSurface_00A_Normal`，本次没有减弱网格几何法线或修改握持轮廓。颜色与微法线都按相同 UV0 变换采样；沿用既有法线纹理的导入方向，不再次翻绿。
- 木材源 `T_WoodSurface_00A_RHAOM` 只使用已知的 R 粗糙度通道，不误称 ORM；微粗糙度集中到新的加工表面范围。合金细纹在局部厘米坐标中计算，约 0.5 mm 周向间距、主要影响粗糙度，像素足迹用于淡出远处细纹；五条既有窄环作有限的反射层次。所有原始纹理保留，不新增底色烘焙阴影或满面划痕。
- 原有雨湿图保留一次，在干燥表面之后计算。四个握柄实例与八个尾饰材料加入原天气表自映射，保留逐物品 `WeaponWetness`。公共木材、元素与金属母材质不改。

## 尾饰实现

四件冰魂坠、雷铃、净化藤和火焰坠保留固定夹环、挂点和坠体，悬绳增加变形分段。UV1 保存相邻物理段索引与混合权重，顶点 R 区分固定夹环（0）和活动部分（1）；坠体全部绑定第 6 段，避免像软胶一样弯曲。FBX 导入的 V 翻转只在着色器还原一次，关闭尾饰自动光照 UV 与 Nanite，保留全精度 UV。

复用镇岳的 `USwordTasselMeshComponent`：8 个引导点、7 段长度约束、重力、惯性、阻尼和有限子步。仅增加可选质量分配，镇岳原默认值保持原样；雷铃采用较重坠体。胶囊约束用于杖身附近的中心线排斥，属于轻量近似，不是坠体网格级 Chaos 碰撞，也不添加环境射线。材质同时旋转 WPO 与法线；停顿、瞬移、切装后沿用原有重置逻辑。

`Content/ColdSteelData/staff-tail-dynamics.json` 随已有 ColdSteelData 目录打包，装配时读取缓存；Tick 不加载资产或配置。第一人称与掉落物通过 `ColdSteelStaffAssembly::Apply` 创建物理尾饰，第三人称通过 `FPSPlayerBodyEquipment` 同样创建组件。每个组件拥有自己的材质实例及链状态；游戏与 PIE 世界启用，预览世界和专用服务器不启用，不复制装饰物理状态，不参与伤害和装备存档数值。

## 生产入口与状态

- 可编辑源：`SourceAssets/ApprenticeStaff20260927/GripTailRefinement20261009/Staff_GripTailRefinement.blend`。
- 参数：同目录 `surfaces.json`、`Export/tail-dynamics.json`；导出清单 `Export/meshes.json`。
- 安装：`install_ue.py` / `run_install.ps1`；编辑器运行时走现有互斥桥，关闭时使用无界面 Python commandlet。
- 正式路径：`/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_grip_lining_*` 和 `SM_Staff_tail_charm_*`；同时保存 V21 对应制作副本。新材料位于 `GripTailRefinement20261009/Materials`。
- 重导：V21 导入器仅在本次 `install-receipt.json.complete=true` 后采用本轮清单，并保护尾饰 UV1、顶点色与动态网格设置。
- 原包恢复源：同目录 `Before/Content`。仅在编辑器不占用对应包时按精确清单恢复；不可在已加载资产上直接覆盖磁盘包。
- 实际资产保存以 `install-receipt.json` 为准；必要编译结果见同目录构建日志。源码、导出与保存状态分开记录。

2026-10-09 本轮已完成后台正式 Editor 构建（`build-editor-final.log`，Result: Succeeded）、D3D12 材质编译及保存。四个握柄和四个尾饰的正式／V21 副本共 16 件网格已保存，三种符文颜色及天气表也已保存；`install-receipt.json.complete=true`。木纹最终环向平铺采用整数倍率，避免原 UV 环绕缝出现新的跳变；Blender 源、配方和三个木材实例同步更新。

初次导入的两个 Python 编辑器属性访问问题已修正；材料成功保存后由 `resume_meshes.py` 接续网格导入，避免重复重建材质。材料阶段回执保存在 `materials-saved-receipt.json`，最终导入日志为 `install-20261009-210244-commandlet.log`，木纹实例保存日志为 `install-20261009-210444-commandlet.log`。

本轮不运行游戏、截图、渲染、回归或视觉验收，由用户测试。材质参数属于本轮制作方案，不能写成已获得用户观感认可。
