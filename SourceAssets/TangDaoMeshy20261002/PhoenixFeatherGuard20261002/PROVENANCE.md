# 来源

- 用户提供的凤仪华羽护手参考保存在 `Reference/PhoenixFeatherGuard_Reference.png`。参考中的文字作为视觉注释，不自动作为新增战斗效果指令。
- 内置 imagegen 生成独立的凤羽、双凤首和卷云浮雕源，已复制到 `Ornament/PhoenixCloud_HeightSource.png`；提示词见 `imagegen_prompts.json`。源中的两处红色定位点用于独立红石建模，不将其印刷到金属表面。
- 在 Blender 5.1 本地生成双面闭合护手、贯通孔壁、真实接口圈、红石和托座。安装环来自原唐刀 `interfaces.json`；闭合板面方法复用同工程璇云龙璧护手，原件保持不变。
- 4K 鎏金 PBR 由同源浮雕高度和本地金属配方生成；红石使用 512 PBR、金属度 0。法线为 OpenGL，UE 导入翻转绿色通道。UE Substrate 材质派生自现有 TangDao SurfaceV2，不修改刀身符文图集。
- 正式图标由实际新护手模型灰阶渲染，再使用内置 imagegen 合成认可金属方框。最终 PNG、UE Texture、可编辑作者场景、FBX/GLB 及保存回执均进入项目目录。
- 原始 imagegen 输出仍保留在 Codex generated_images；正式依赖均已复制入工程。用户参考图的公开再分发许可未由本次制作认定，本次没有公开发布。
