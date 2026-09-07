# 握姿和涂层支持模块发布

本批只发布自编、未自动接入远端主场景的支持模块：foregrip_pose、foregrip_finger_pose、attachment_material_match、weapon_finish shader 与 HK416 clean coating shader；以及对应技能复查规则。模块输入由调用方提供骨架、配件节点、纹理和骨架映射。没有复制模型或组合手模，也没有硬接入较旧远端 Gun/HUD。

本地完整接入已完成，16 项专项测试与五枪游戏内复核见本地 docs/gunsmith-full-review-20260907.md。远端缺少本地视模、配件场景、五枪资源与部分共享运行依赖，公开源模型/手模和原声音效的再分发待办仍按 docs/firearm-publication-20260906.md 保留。本次公共模块验证不替代完整远端游戏集成验收。

## 接口约定

foregrip_pose 使用 restore → 原动画评估 → advance → apply，每个动作调用 begin。profile 提供 upper/lower/hand、fingers、separate_hand、return_times 与 equip_return；part 位于武器 Skeleton3D 的 BoneAttachment3D 下，提供 HandTarget 和可选 GripPoseFrame。完整绑定只在本地调用方存在，本次不导入任何外部资产。

attachment_material_match 使用调用方材质资源与 receiver 节点，通过 rifle_clean_profile 匹配深灰材质；镜片/发光材质不覆盖。两个 shader 的纹理由调用方赋值，公共测试使用程序生成的纯色纹理，不打包外部素材。

## 整理

34 个由最终 61 帧连续预览替代的中间文件已归档到 E:/无尽轮回/3d/trash/grip-equip-v03-superseded-20260907/，manifest.txt 记录文件名。包括旧 after.gd、after.log/err、after-contact.png 与 30 个离散 after 帧。保留原动作对照、修正后连续帧/GIF、最终日志、源工程和材质来源。trash 中间图不上传 Git。

本地 master 与 origin/main 各有25项差异，使用 origin/main 的独立 detached worktree 发布，未混入主工作区其他提交或改动。

## 本批独立验证

将精确发布文件复制到无外部模型/纹理的最小 Godot 项目，运行 tests/test_published_grip_materials.gd：程序化骨架回握、速度缩放、覆盖恢复、配件匹配幂等、保护材质与两个 shader 的 Forward+/D3D12 实际渲染通过，无脚本或 shader 错误。技能 quick_validate 通过。正式远端主场景未改，本次不宣称完整动画枪械集成已发布。
