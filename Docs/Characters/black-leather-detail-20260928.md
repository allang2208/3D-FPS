# 黑色皮革手套：参考图细节制作

后续毛面材质、浅层视差和实体加厚腕口见 [V2 制作记录](black-leather-relief-cuff-20260928.md)。下文保留第一版源与接入记录。

目标物品为现有 `ue_field_gloves_black`。保留全指、V7 接触包络和所有原生绑定，参考用户给出的黑色战术手套画面提高拼片、缝线、皮纹、织物插片和磨损细节。仅修改这一物品的装备与展示引用。

## 制作方案

1. 导出当前 22 套装备网格，保留原生骨架、权重与腕口边界。以 M4 为共同设计空间，在手背增加柔软护垫、主裁片和腕口束带；接触侧保持原位置。
2. 使用毫米尺度的皮革颗粒、边缘压线、双道针脚、折痕及局部磨损。局部加入黑色织物和低饱和织标，避免整件只有一种均匀皮纹。采用项目已有扫描皮革，保留其来源记录。
3. 制作真实细分与位移高模，保留可编辑的几何母版与程序化材质；把细节烘焙为游戏用 BaseColor、ORM、切线法线。游戏网格保留可见护垫起伏，细小针脚和颗粒使用烘焙法线。
4. 使用独立资产目录，沿各武器原生绑定派生，三级 LOD，不新增运行时动画、布料求解或逐帧逻辑。保留现有装备 ID 与战斗数值。
5. 用最终游戏网格和同一材质制作空手套掉落模型与 320×320 透明装备图标，再保存 UE 资产并更新此物品配方。

作者目录：`SourceAssets/BlackLeatherDetail20260928/`。
资产目录：`/Game/Characters/ModularOutfit20260924/BlackLeatherDetail20260928/`。

## 已完成作者源

- 第一人称高模：1,134,942 顶点、1,124,448 个多边形面（细分后的面主要为四边形，不能将此数写成三角面数）。Body 高模：1,252,980 顶点、1,245,312 个多边形面。
- 原生游戏网格保持双手 23,426 三角面、单手 11,713 三角面、Body 25,944 三角面。采用高模向低模投射法线，材质颜色和 ORM 独立烘焙。
- 第一人称共享 4096×4096 BaseColor / ORM / OpenGL Normal，Body 为独立 2048×2048 贴图组；UE 法线导入翻绿。ORM 为 R 遮蔽、G 粗糙度、B 金属度。皮革、织物和缝线均为非金属。
- 细节包括柔软手背主裁片、四指背侧衬垫、双道针脚、指侧走线、指关节压痕、掌面补强与折线、腕部束带、黑色织物和原创低饱和织标。高模具备实际针脚与压线起伏，微皮纹同时使用项目现有扫描素材。
- 材质来源：`SourceAssets/HandEquipmentAppearance/Source/xjghdgl.json` 及同目录扫描贴图。用户参考图仅用于风格和结构参考，存于作者目录 `Reference/black-glove-reference.png`；未提取原图品牌标识或声称复原原模型。
- 高模为静态雕刻/烘焙源，文件内同时保留绑定原生骨架的游戏网格。其余 22 套原生派生数据保存在 `Authored/`，支持重复导入；未新增动画。
- `M4_BlackLeather_HighPoly.blend`、`Body_BlackLeather_HighPoly.blend` 保留高模、游戏网格、作者材质和贴图；`BlackLeatherDetail_Presentation.blend` 保存正式空手套展示与图标场景。
- 已制作独立掉落 FBX 和 320×320 透明图标，使用最终游戏材质；图标制作不代表游戏内渲染验收。

## 已保存并接入

- 后台 commandlet 成功完成导入并退出，日志末尾为 `BLACK_LEATHER_DETAIL_PUBLISHED ue_field_gloves_black 22`。
- 保存 22 个骨骼网格、6 张纹理、2 个材质和 1 个掉落静态网格，共 31 个独立 UE 资产；网格使用三级 LOD。
- 已更新 `modular_outfits.json` 中黑色手套的 22 套 `rig_meshes`，清空统一材质覆盖，由各网格保留自己的第一人称或 Body 烘焙材质。覆盖区域沿用 V7 的 `[2]`，不更改裸手、其他手套或上衣。
- 已更新 `items.json` 中同一物品的说明、掉落模型、材质与图标路径，物品 ID、装备槽和战斗属性保持原值。新图标位于 `Content/ColdSteelData/Icons/BlackLeatherDetail20260928/ue_field_gloves_black.png`，背包、装备栏和仓库继续使用同一物品图标。
- 作者回执：`SourceAssets/BlackLeatherDetail20260928/published.json`；保存日志：`Saved/black-leather-commandlet-20260928-01.log`。原引用保存在作者目录 `before-recipe.json` 与 `before-publication.json`。
- 接入开始时原编辑器桥批次异常退出，本任务未发送该轮写入。编辑器已关闭后，等待既有后台进程结束，改用互斥的无界面 commandlet 完成导入；没有主动打开编辑器或游戏。

未进行游戏测试。重新进入游戏后装备现有“黑色皮革手套”即可查看；实际抓握、换弹、穿插和光照表现由用户测试。
