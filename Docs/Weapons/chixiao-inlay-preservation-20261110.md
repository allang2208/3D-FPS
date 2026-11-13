# 赤霄红色嵌条与剑身材质改造

用户反馈赤霄改造刀身的红色部分消失。本次限定修复赤霄的材质覆盖范围。

## 原因

赤霄的暗红嵌条与两侧贴图金边由 `ChixiaoBladeV1/author_blade.py` 写入原生 BaseColor，和钢质刀身共用 `M_Chixiao_BladeSurface` 槽。刀根立体金色云纹使用独立的 Brass 槽。

活动材质图的 `SharedTwoHandFinish20261101V1` 四路 PBR 节点将保护遮罩接到常量 0，因此非原厂剑身材质会覆盖红色嵌条和贴图金边。原生贴图仍被正确引用，问题发生在其后的材质混合。当前旋风版本仍使用原生 PBR，没有该覆盖分支。

## 修改

- 在赤霄私有材质中复用原生底色采样，以其红色色度区分暗红嵌条、黄铜金边与偏冷钢质底色；保护区跟随原 UV、双面映射、渐变端部和 mip 过滤，无新增纹理采样。
- 同一个保护范围连接底色、粗糙度、法线、金属度，并约束陨铁的各向异性与切线。原厂模式保留原生输出，其他材质继续覆盖钢质主体。
- `SharedTwoHandMaterials20261101/install_materials.py` 和赤霄原资产安装器接续同一修复配方，避免重新制作后丢失区域保护。

制作入口：`SourceAssets/ChixiaoInlayPreservation20261110/install_material.py`。活动资产：`/Game/Weapons/Zhanmadao20261018/ChixiaoBladeV1/Materials/M_TangDaoBladeRuneSurface_Zhanmadao_chixiao_V1`。修改前资产保存在该制作目录的 `BeforeAssets/`。

## 交付状态

源码配方已落盘。原编辑器退出后，已通过无界面 commandlet 编译并保存上述正式材质，进程退出码为 0；保存回执为制作目录的 `material-receipt.json`，构建日志为 `save-20261110-214236.log`。本次无需 C++ 构建。

未运行游戏、截图、渲染或回归，外观由用户自行体验。
