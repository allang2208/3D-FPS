# PKM RightHand52 — 拉栓手部骨骼与权重

2026-09-28，继续 RightReload51，根据用户反馈调整 PKM 拉栓手部骨骼和蒙皮。

读取 SKILL：`ue5-fps-arms-animation/references/pose-contact.md`、`grip-arm-refinement.md`、`casting-arm-volume.md`、`bow-hand-string-contact.md` 和 `accepted-bare-hands.md`。执行要点为分指自然抓握、实际蒙皮接触、完整骨段辅助骨、原生参考骨架和本枪局部派生。

## 制作

- 从当前五条空仓换弹原始姿态继续，不覆盖 RightReload51 的合盖、整臂、拉柄和音效时序。
- 在 4.99–6.04 秒区间调整右手五根末节骨的局部旋转；食指末节旧姿态的旋转向量主要弯曲分量约 74°，本轮降低至约 46°；拇指减轻过卷和侧向扭转，其余手指分别收敛。数字为本骨架局部旋转参数，不是人体关节角或跨骨架阈值。
- 后拉增加轻微扣紧，后止短停，前推期间逐渐卸力，前止后才交回原松指轨迹。手指局部平移、骨长、掌骨及原食指/中指中节接触轨道保持。
- PKM 裸臂右前臂/腕掌 2,462 个制作源顶点按实际骨骼站位分配权重；1,971 个已混合的右指关节顶点只在同指拓扑邻域内做两次小幅平滑。保留几何、UV、法线、左侧及共享母版。
- 同步当前露指手套 TailoredFingerlessV1、黑皮手套 BlackLeatherStitchWearV4 与衣袖。新版手套通过同侧、同指区域的裸手表面重心插值同步权重，保留其当前造型和材质。
- 同时更新露指手套实际运行使用的「手套＋外露皮肤」组合网格，避免只改单独手套却漏掉组合版本。

## 已保存

6 份 UE 网格：独立 V7 PKM 裸臂、PKM 原生视模、露指手套、黑皮手套、衣袖、露指手套及外露皮肤组合网格。按原数量重建 LOD。

5 条空仓换弹：原厂、vertical、canted、prism、angled。每条只更新五根右手末节骨轨道，保持 6.60 秒与上一轮时钟。

`install_receipt.json` 的 `complete=true`、`combined_skin_saved=true` 记录实际保存。初次桥接因编辑器关闭未发送操作；随后使用后台 commandlet。旧手套制作源不匹配当前网格时，在保存手套前停止，继而切换至当前制作源完成。未重启图形编辑器。

`Authored/` 为最终轨道及各网格权重；`source_paths.json` 和 `skin_source_path.txt` 为当前真实制作源映射。`Before/` 为本轮修改前资产及源备份。阶段安装脚本带版本保护，属于本轮执行记录，不能无条件重跑旧阶段脚本覆盖新状态。

`Editable/PKM_RightHand52.blend` 包含当前骨架、裸手绑定及五条完整动作；`PKM_TailoredFingerlessV1.blend`、`PKM_BlackLeatherStitchWearV4.blend` 为本轮新版手套权重编辑副本，使用中性材质；外观制作母版未被中性材质副本覆盖。

权重是 PKM 共用网格数据，影响其右手在其他动作中的变形；动作轨道仅修改空仓拉栓区间。未做本轮游戏、渲染或测试验收，由用户测试形变、抓握和动作过渡。
