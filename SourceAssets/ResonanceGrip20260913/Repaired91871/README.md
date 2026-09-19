# 共振握把 91871 修整与接入

2026-09-13。用户接受“修整后接入”，冻结 seed 91871。

## 已完成

- 以生成母版为基础，补合小边界环、局部整理后支柱表面，并重建双侧共 16 个六角凹槽螺丝头。边界环统计包含 UV/顶点接缝，不能视作实际破洞数量。
- 按现有 M4、AKM、QBZ191 安装参考分别适配尺寸和方向，保留顶部安装区域，对近手部表面进行局部避让。
- 保留 angled_foregrip 配件身份、原有数值及所有抓握动画。未编辑手骨或动画动作。
- 金属分别使用各枪现有涂层来源，聚合物使用独立深色微表面。材质分区邻接按空间顶点连接处理，修正 UV 接缝导致的零散错误分区。
- 运行时三把枪的模型引用切换至 /Game/Weapons/ResonanceGrip20260913/Repaired91871/{M4,AKM,QBZ191}/SM_ResonanceGrip。
- 原生构建成功，记录在 Game/build_stdout.log。最终资产由 Game/import_assets.py 导入，共享正式 Content 的 ImportHost 避开当前主工程 AutoFootstep 默认对象注册冲突。

## 质量与限制

- Game/Review 为 Blender 实际网格渲染；已查看最终 M4 材质图，零散面片材质斑点已消除。
- 自动减面损伤表面，因此本版保留母版，约 491757 三角面。尚未完成生产低模优化，需要专门重拓扑。
- 内框、部分螺丝座仍有生成网格起伏，不应表述为精密硬表面成品。
- AKM、QBZ191 手部避让使用既有安装范围映射，不代表逐帧实机接触验收。
- 未启动游戏或做运行测试，游戏中贴合、不同动作穿模及性能由用户测试。编辑器需重启加载本次原生构建。
- UE 导入可能提示近零副切线；本次未做 UE 渲染验收。

## 文件

- RepairedMaster.blend / .glb：修整母版。
- Game/{M4,AKM,QBZ191}/ResonanceGrip_Surface_Editable.blend：可编辑源。
- Game/{M4,AKM,QBZ191}/SM_ResonanceGrip.fbx：引擎导入源。
- Game/import_results.json / import_host.log：导入回执及日志。
- Game/Review/91871_quarter_material.png：最终 M4 材质预览。

ImportHost/Content 为正式 Content 的目录联接，不要递归删除该路径。
