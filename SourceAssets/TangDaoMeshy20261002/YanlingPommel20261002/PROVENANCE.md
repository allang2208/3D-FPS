# 来源与制作记录

当前运行修订为 `ConeV3`。用户提供的总体图与锤头细节图保存在 `Reference/`，作为几何和纹饰参考；图中标注文字没有被当作新的玩法指令。

八面锥、连续折线甲框、连接环和真实接口在 Blender 5.1 中精确建模。龙云纹饰使用内置 imagegen 重新生成灰度雕刻素材，原图、提示词保存在 `ConeV3/Ornament/` 与 `ConeV3/imagegen_prompts.json`。软透明晕圈不参与浮雕高度；材质遮罩和几何高度从同一细纹配方派生。

锻钢／鎏金使用 4096 PBR，漆面使用 512 PBR。BaseColor 为线性金属反射色转换到 sRGB；ORM 为 AO／Roughness／Metallic，Normal 为 OpenGL，UE 导入翻转绿色通道。三个 Substrate 材质克隆自当前 TangDao SurfaceV2，另存旋风时序响应材质副本，不更改刀身符文。

改造图标由实际 V3 模型灰阶渲染后使用内置 imagegen 沿用认可的金属框，素材、最终 PNG 与 UE Texture 均保留。三维材质保留锻钢和暖鎏金。

旧版本源及资产保留。用户参考图的公开再分发许可未由本次制作认定；本次没有公开发布。未开展游戏测试或视觉验收。
