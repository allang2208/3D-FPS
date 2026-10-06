# 灰钢锁子甲裤

依据本对话已选概念图制作独立裤装 `ue_chainmail_pants`。沿现有 Jason 裤装取得尺度、完整参考骨架和原生权重；裤身拓扑、裤腿轮廓、裆部、护腰和护膝重新制作，不覆盖原牛仔裤与工装裤。

## 结构

- 腰腹和臀部连续裁片，裆部弧形桥接；大腿留量，小腿逐渐收拢，保留膝后柔软锁甲区域。
- 腰部八块钢片，左右胯部各三片短叠片，腰扣、铆钉及钢边使用实体几何。
- 两侧凸面膝盖罩、上下独立叠片与绑带；膝盖罩使用大腿/小腿混合权重，叠片分别随对应骨段。未增加骨骼、碰撞求解、逐环组件或 Chaos Cloth。
- 腰口和脚口具有内壁、回折与实体包边；深灰衬层独立材质槽。
- 普通版与 BootsFit 版各 39,824 个 LOD0 三角形；后者扩大下段裤腿，仅在穿戴 `ue_boots` 时使用。LOD 沿现有服装入口生成三档。
- 背部与内部结构依据人体和装配关系设计；概念图未提供被遮挡侧，不称作精确扫描还原。

## 材质和来源

- 锁甲沿用 `ChainmailInterlace20260929` 的真实周期环纹烘焙，UV 以 25 cm 为基准；使用标准 Body 材质，POM 深度为零，保留纹理流送。
- 甲片新制 6.25 cm 周期锻钢高度场，保存完整 `.npz` 源与 Blender 烘焙母版；输出 1024² BaseColor、Normal、ORM。法线是 OpenGL 约定，UE 导入翻绿；ORM 为遮蔽/粗糙度/金属度。
- 宏观弧度、厚度、叠片和包边由网格承担，材质仅表达细锻纹与拉丝。钢片、锁环和深灰衬层分三槽保存，配方不使用单一材质覆盖。
- 比例与蒙皮参考为已导入的 MetaHuman Jeans/Jason；授权原始来源沿此前裤装记录保留。新构件与作者代码为本轮制作。未作公开资源分发。

## 制作文件

- `SourceAssets/ChainmailPants20261004/Concept.png`：本对话所选概念图。
- `SourceAssets/ChainmailPants20261004/ChainmailPants.blend`：分件、完整 Jason 绑定、标准版与靴子版、烘焙源。
- 同目录 `Jason_ChainmailPants*.json`：厘米制几何、法线、UV、骨骼、权重和材质槽。
- `Tools/ChainmailPants/author_geometry.py`：尺寸、结构与蒙皮作者入口。
- `Tools/ChainmailPants/bake_steel.py`、`save_editable.py`：表面生产与可编辑源保存。
- `Tools/ChainmailPants/save_assets.py`：UE 网格、LOD、材质和展示/掉落资产落盘。
- `Tools/ChainmailPants/publish_catalog.py`：仅新增本物品数据，不写玩家库存或存档。

## 接入合同

裤装槽 `15`，装备栏继续使用现有布局；仅 Jason 第三人称/身体穿戴，不给第一人称手臂挂裤装。沿 `shoe_fit_meshes` 切换皮靴配套裤脚。皮肤覆盖引用当前牛仔裤配方，保留独立鞋靴覆盖合同。

物品为 2×3 格，普通品质，初始基础防御 40、价格 65；无新增减速或攻击速度惩罚。数值作为本轮初始配置，不代表平衡测试完成。拾取、装备、仓库与存档沿既有通用物品系统。

目标资产根：`/Game/Characters/ModularOutfit20260924/ChainmailPants20261004`。
正式图标：`Content/ColdSteelData/Icons/ue_chainmail_pants.png`，从实际已保存展示网格与三槽生产材质出图，213×320 透明 PNG。

## 本轮状态

可编辑母版、烘焙贴图、两套穿戴网格、三档 LOD、三槽生产材质、静态掉落和图标展示网格均已保存。`items.json` 与 `modular_outfits.json` 已新增 `ue_chainmail_pants`，沿既有通用接口接入。没有原生源码变更，本轮无需编译 FPSGAME 模块。

现有桥未发现可连接的编辑器节点，未执行写入；随后在共享批次互斥内通过后台 commandlet 保存独立新目录。保存回执为同目录 `saved_assets.json`，配置发布回执为 `published.json`。

正式装备图标已出图并保存到 Content，同时在作者目录保留副本。首次出图因纹理驻留等待超时结束；仅对离线图标命令启用 `-NoTextureStreaming` 后完成，未修改运行时流送设置。生产结果由 `icon-production.log` 和 PNG 记录，首轮日志保留为 `icon-production-streaming-attempt.log`。

遵守后台制作规则；未启动游戏、PIE、检查脚本、动作/穿模验收或性能测试。站姿以外的实际效果由用户测试。

## 护膝与护腰修订 V2

用户指出 V1 护膝、护腰粗糙，圆盘护膝偏离参考图。当前修订的制作入口为 `Tools/ChainmailPants/refine_armor.py`，来源与回执放 `SourceAssets/ChainmailPants20261004/ArmorRefineV2`。

- 护膝按参考图描成上宽下收的弧面盾形，明确肩部、侧边与下端收拢；移除旧圆盘与通用圆环边框。
- 一片上叠片、两片下叠片围绕盾形甲面搭接，边界弯曲且下方逐渐收窄；保留大腿/小腿区域的原生绑定关系。
- 主腰带加宽，前腰搭扣采用扁平压片；左右髋部各两列三层甲片，前边缘延伸到前侧，斜切下缘和圆角形成轮廓。
- 新甲片具有闭合内壁、三段几何倒角及实体铆钉底座；钢面使用粗糙度约 0.48 的同源锻纹烘焙，细表面与宏观轮廓分别制作。
- 原裤身、裤口内壁和包边的顶点、UV、法线与权重逐块保留；膝部绑带保留形体与权重，仅为其原先退化的内壁 UV 补齐有效表面坐标。标准/皮靴两版同步。装备 ID、槽位、防御、价格与玩家存档不变。

V2 每套 LOD0 作者网格为 169,253 三角形，包含新甲片、倒角、搭扣和铆钉；保存三档 LOD，不由几何数量推算性能收益。可编辑源分别为 `ArmorConstruction.blend`（新构件）与 `ChainmailPants.blend`（完整穿戴母版），盾形轮廓记录在 `shield-contour.json`。

首次 UE 保存出现近零切线提示，制作定位发现绑带内壁的旧 UV 退化以及少量新倒角的退化小面。作者入口已加入倒角残余面清理与这些表面的局部 UV 修正；原先的导入日志保留为 `save-assets-before-uv-repair.log`。此记录是处理制作告警，不是游戏着色或动作验收结论。

UE 标准版、皮靴版、静态展示和掉落资产已保存到独立 `ArmorRefineV2` 资源目录，穿戴与物品配置已发布；落盘回执为 `saved_assets.json` 和 `published.json`。旧存档实例保留最初创建时的静态图标/掉落路径，已用 `update_saved_instance_meshes.py` 将这两个既有资产同步到新版，完成回执为 `existing-instance-assets-saved.json`；旧静态资产备份在 `PreviousStaticPackages`，未直接改写存档。

后台制作批次已完成（`CHAINMAIL_ARMOR_V2_BACKGROUND_COMPLETE`）。正式装备图标已从新版展示资产重制，保存到 `Content/ColdSteelData/Icons/ue_chainmail_pants.png` 并在 V2 作者目录保留副本，生产日志为 `icon-production.log`。

本次没有启动游戏、动作验收或额外预览渲染；正式物品图标从实际保存模型重制。

2026-10-06 整理：本文历史备份／旧版本路径按 [归档清单](lower-equipment-archive-20261006.json) 映射到 trash。当前制作入口与恢复顺序见 [整理发布](lower-equipment-publication-20261006.md)。
