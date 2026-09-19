# ASH-12 扩容弹匣中段深色块修复

用户要求排查并修复中段深色材质。根因是顶点材质区域遮罩，而非装错另一把枪的材质。

原厂两个弹匣材质槽的 SurfaceRegions 均为 (0,0,0,1)。扩容制作新增的 BMesh 面未显式填写此颜色层，29,043 个角点变成 (1,1,1,1)。ASH Surface 材质通过 R/G/B 区分聚合物、裸露枪机钢与枪口内壁；白色最终启用了 B 通道的暗色内壁，造成中段色块。

本轮仅将这些遮罩改为原厂的 (0,0,0,1)，几何、UV、法线及抓握坐标未变。原 ASH12ExtendedMagazine20260919/author.py 也补上最终遮罩写入，防止重导重现。

- 模型：ASH12_ExtMag30_Finish_Editable.blend。
- 导出：SM_ASH12_ExtMag30_Finish.fbx。
- 引擎：/Game/Weapons/ASH12/MagazineFinish20260919/SM_ASH12_ExtMag30_Finish。
- 材质沿用现有 ASH 连续材质及原厂底板材质，干湿映射均继续生效。
- 图标移除编辑源中残留的旧图案 BaseColor，改用当前 UE ASH 材质的常量基色；保留结构法线、ORM 与统一朝向。

完成顶点颜色定位、离线模型材质对照、导入及必要构建。未进行 PIE/换弹/天气实机回归，交由用户测试。
