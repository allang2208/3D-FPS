# 第一人称低头尖刺：定位记录

用户已认可 `OwnerBodyFrontV2_20261005` 相机位置，禁止以此次修复再次改变视点。手枪画面存在粉色锯齿，用户说明任意衣服均有；随后步枪画面仍出现黑色尖面。此前 `pistol-body-depth-20261006.md` 的深度缩放只覆盖手枪，因此步枪截图本身不能证明袖子蒙皮损坏，也不能证明手枪修复已通过实机体验。

用户最终要求“先离线处理，不再读取现场”。本轮从已保存的静态源网格确定了本机上衣肩口的整面裁切缺陷，并制作、保存和接入连续切口替代资产；没有改 C++ 或已认可的相机参数。尚未把截图中的具体尖面与运行组件一一对应，不能将本次资产保存表述为实机问题已消失。

## 读取中断

用户明确保持现场后，`Tools/FirstPersonLegs/read_sleeve_spike_inputs.py` 使用 `GeometryScript_SceneUtils.copy_mesh_from_component` 读取活动蒙皮网格。2026-10-06 11:59:42 引擎在 `ModelingComponents` 中触发数组越界：`36138 into an array of size 984`，编辑器随后退出。操作没有保存或修改资产，也没有自动重启编辑器。已经向用户说明该崩溃由本次读取触发。

该接口内部调用 `GetCPUSkinnedVertices`，不再用于本项目活动的 LeaderPose／隐藏材质网格读取。脚本现已移除该转换，改为仅记录组件引用、可见材质段、LOD、相机和骨骼变换，并逐组件落盘。静态资产几何应独立从资产读取，不再经活动组件做 CPU 蒙皮转换。

失败期间只得到 `FirstPersonSharedBody.json` 的空几何（驱动组件不可用于定位）；`active.json` 仍是此前无游戏世界的记录，不视为成功现场。响应与数据保存在 `SourceAssets/SleeveSpikeRepair20261006`。按用户最新要求，停止现场读取，不再等待用户恢复现场；后续仅离线制作。

## 静态源中找到的具体缺陷

`read_sleeve_assets_offline.py/.ps1` 在独立 `NullRHI` Python commandlet 中读取已保存的三件世界上衣、本机上衣、M4 衣袖和七分裤。没有调用活动组件转换，也没有保存源资产。输入在 `SourceAssets/SleeveSpikeRepair20261006/Assets`。

旧本机上衣与世界源的顶点和权重一致，但 `save_shared_body_shirts.py` 按一个三角面的平均手臂权重是否大于 0.4，决定是否隐藏整个面。因此肩口显示边界沿原始三角形边缘跳变。三件上衣新增的隐藏边界最长边分别约 5.60、4.88、4.72 cm；这是离线源的几何问题，不是已确认的截图归因。

## 本轮已落盘的处理

`save_continuous_owner_shoulders.py/.ps1` 从当前世界源重新派生本机上衣。沿 `upperarm_l/r` 后代骨骼权重之和的 0.4 等值线，在跨界三角形内部插入交点，将肩口两侧分别划入原可见材质和隐藏袖臂材质。新顶点插值源位置、各 UV 通道、法线和原生骨骼权重；未跨界的原面继续保留。原世界上衣和各武器第一人称衣袖、手套、手臂动作没有回写。

| 上衣 | 被分割的原面 | 替换子面 | 隐藏材质编号 |
| --- | ---: | ---: | --- |
| 野外长袖 `ue_field_sweater` | 704 | 2112 | 5–9 |
| 炭灰短袖 `ue_field_sweater_charcoal` | 757 | 2271 | 5–9 |
| 锁子甲 `ue_chainmail_shirt` | 741 | 2223 | 3–5 |

三件实际保存的网格及各自 LOD policy 位于 `/Game/Characters/ModularOutfit20260924/OwnerShoulderSeam20261006`，网格名仍为 `SK_Jason_Owner_<物品 ID>`。本机三个 LOD 保持完整切口拓扑和最多八个权重，防止分区交界独立简化重新改变肩口；此设置只影响这三件本机派生资产。资产 commandlet 于 2026-10-06 12:27:45 完成，退出码 0。

`publish_continuous_owner_shoulders.py` 已将 `modular_outfits.json` 中这三件的 `owner_body_meshes[Jason]` 和 `owner_body_hidden_materials[Jason]` 更新到新资产。只替换对应 JSON 条目，保留其余配置与并行修改。旧 `publish_shared_body.py` 同时改为采用本次保存回执，避免后续重新发布时退回旧整面裁切。旧资产保留。

回执为 `saved_shoulders.json` 和 `published_shoulders.json`，资产保存日志为 `save-shoulders.log`，发布前配置备份为 `before-shoulder-publish-modular_outfits.json`，均在 `SourceAssets/SleeveSpikeRepair20261006`。没有新增 C++ 修改，因此本轮不需要 DLL 构建。已接受的 56 / 62 / 12 / 0 / 40 cm 相机参数未改变。

## 交付边界

已完成资产制作、后台保存和配置接入；下一次游戏初始化读取新配方。生产轮次未启动编辑器、运行游戏、切枪、截图或追加验收测试。

2026-10-06 用户随后明确反馈“没问题了”，并要求复查本轮开发内容。此次视觉问题按用户反馈记为已解决，不再调整已接受的模型、镜头和动作。后续离线复查、两处逻辑／发布修复及验证边界见 [开发复查](equipment-review-20261006.md)；用户认可不等于自动完成全武器、全动作的回归测试。
