# 书柜隔板与侧板接缝修复

用户截图中的医疗档案书柜复用 `SM_Staff_BookcaseBody_V4`。原配方将内部木隔板制作成柜体外宽 96 cm，而两侧各有 3 cm 厚侧板；隔板端面与侧板外表面重合，形成截图中的横向木纹闪烁条。隔板后缘也与背板外表面重合，顶板与侧板、背板存在高度重叠。

已修改 `SourceAssets/DungeonStaffLiving20261002/Scripts/author_scene_polish_v4.py` 的 `bookcase_v4`：

- 底板及三层内部隔板宽度改为柜内净宽 90 cm。
- 隔板前缘内收 6 mm，避开侧板前缘圆角；后缘止于背板内表面。
- 保留原顶板外形，侧板与背板上端收齐至顶板底面 194.25 cm。
- 保留书本、材质、柜门、铰链、容器身份和场景位置，碰撞板件随对应几何更新。

单独导出并重导入原共享网格 `/Game/Dungeons/StaffLiving20261002/ScenePolishV4/Meshes/SM_Staff_BookcaseBody_V4`，已保存资产。复用同一网格的宿舍和医疗区域直接使用修正后的柜体，无须重建房间。8 个材质槽、10 个简单碰撞凸包及原 Nanite 设置保留。

制作源同步到 ScenePolishV4、RoomDetailsV5、WallInsetV6、CoffeePolishV7 的 Blender 合集中，各自仅替换该柜体及相应碰撞网格，原摆放与柜门保持不变。独立制作入口与保存回执位于 `SourceAssets/DungeonStaffLiving20261002/BookcaseJoints20261010`，修改前文件保存在该目录的 `Backups`。

已完成制作、导出、导入和资产保存；未运行游戏、渲染或视觉验收，效果由用户测试。
