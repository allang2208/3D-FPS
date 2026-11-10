# 强化工作台第二轮调整
## 目标与范围
按用户截图与 2026-11-08 反馈直接接入：材料文字化、删去重复消耗汇总、展开武器强化实值；金／蓝成功粒子更明显，桌面原法阵亮起。保留原尺寸背包、实体台面相机、库存来源、支付、存档和多人权威事务。
## 布局与状态
- 材料是自然高度的两列短文字：材料名×需要量、持有量；不足用红色标出缺口，无图片、卡片或材料滚动条。附魔卷轴目录保留原选择卡及过滤。
- 删除详情底部消耗汇总。实体面板属性表自然展开，移除原 260px 表体限制，共用主体纵向滚动；标题、页签与确认固定。非实体面板仍保留四列表头。
- 未选择、满级、无卷轴、材料不足、等待服务器沿用现有报价与禁用状态。Esc／拖放／取回仍走原入口。
## 数据合同
- 表格以当前实例和报价 After 为准，保留当前角色、配件、品质；基础比较仅清除强化等级与附魔效果。
- 枪械、近战、锤与工具、弓分别读取现有共享评估器。法杖／魔法书显示实际装备魔攻，防具显示物防和已声明魔防。
- 显示当前→加工后→差值；伤害或装备魔攻补充提升百分比。伤害分项按本次详细显示要求展开，不把武器类型套错。无关的零值附魔行不占空间。
- 本次不修改伤害公式、属性、材料数量或保存字段，Refresh 事件驱动，不增加属性 Tick。
## 成功特效与资源
- 强化金色、附魔蓝色：最多 96 核心光点＋32 柔光层，汇聚、凝亮、上浮、淡出共 3.6 秒。
- 基于真实轮廓有界采样；缺少 CPU 轮廓数据时不伪造矩形，桌面法阵仍可独立亮起。
- 仅修改 V6 两个真实符文材质的发光输出，保留原遮罩和 PBR。默认脉冲 0，临时 MID 随成功触发，停止／更换／退出还原原材质。作者脚本保留同一增量构建。
## 文件与交付
UI: ColdSteelEnhancementLayout.cpp、Widget.cpp/.h、新增 Comparison.cpp。
VFX: EnhancementRitualEffect.cpp/.h、EnhancementWorldView.cpp。
资产制作: ArcaneWorkbenchV6_20261107/Scripts/patch_ritual_pulse_v6.py 与 author_materials_v6.py。
必要 Editor 常规构建后，后台 Python commandlet 保存两个符文材质。不启动交互编辑器、不运行游戏、截图、性能采集或验收；由用户体验。未提交或推送。

## 实际落盘结果
- 全部 UI／特效源码已进入常规 FPSGAMEEditor Development Win64 构建。已有共享构建完成 Comparison、Widget、RitualEffect、WorldView 编译；随后本任务完成最终 Layout 增量编译与正式 DLL 链接，Result: Succeeded。最终日志：Saved/BuildEditor/build-20261108-130201.log（4 actions，22.85 秒）。
- 后台 Python commandlet 已实际保存两份原路径符文材质：M_EW_Rune_inlay_energized_recessed_copper、M_EW_PROJECT_carved_stone_work_surface。回执：SourceAssets/ArcaneWorkbenchV6_20261107/Receipts/ritual-pulse-v1.json，stage=ritual_pulse_saved，两个 changed=true，进程退出 0。
- 初次保存因 Desaturation 输入显示名为空而在保存前失败；按引擎接口改用默认第一个输入后完成。成功日志：SourceAssets/ArcaneWorkbenchV6_20261107/Receipts/ritual-pulse-v1-cmdlet-retry1.log。未覆盖原发光遮罩或其他 PBR 通道。
- 未运行游戏、交互编辑器、预览、截图、性能／联机／打包测试；实际视觉与操作体验交由用户测试。未提交或推送，其他并行源码与资产未回退。
