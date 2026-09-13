# 混元手电候选 V3

用户拒绝此前手电的生成细节及本地硬表面重建版本，明确要求改用混元 3D。

- 生成入口：Tools/AssetPipeline/hunyuan3d.ps1，腾讯 TokenHub，hy-3d-3.1，PBR 开启。
- 输入：reference.png，由原手电三视图整理为单个三分之四前侧视角。展示筒身、五道散热环、灯头反光杯及安装鞋。
- 请求记录：Saved/Hunyuan3D/Candidates/flashlight_hunyuan_20260913_v3/manifest.json。
- 本次为新的生成候选，保留 TRELLIS 原版和 HardSurfaceV2。概念参考图不代表实际生成模型质量。
- 用户随后授权替换游戏版本，接入记录见下文；不自动执行游戏测试或验收渲染。

生成已完成：flashlight_hunyuan.glb 为混元原始带材质结果，Flashlight_Hunyuan_Editable.blend 为未重建的可编辑源。原始 ZIP 保存在上述候选任务目录。生成阶段原始文件保持不变；后续适配文件独立保存，未执行游戏测试或预览渲染。

## 游戏替换完成

M4/AKM/QBZ191 均通过 author_hunyuan.py 适配当前护木真实连接面，使用混元几何约 35000 三角形目标，保留 UV0、光学/橡胶分区与原生法线贴图。金属涂层沿用各枪标准；QBZ191 通过 bake_hunyuan.py 烘焙至自身 UV1。新路径 /Game/Weapons/TacticalDevices20260913/HunyuanV3/<family>/flashlight/SM_TacticalDevice 已由 TacticalDeviceComponent 加载，图标、枪匠、角色与掉落共用装配入口。import_hunyuan.py 已导入三枪，installed.json 与 import.log 记录产物。

手电设置：850 lm，40 m 衰减范围，内锥 9 度、外锥 30 度，中性微暖白，0.6 cm 光源半径及 0.9 cm 柔化半径，动态阴影。15–150 cm 近墙距离平滑调整至 85–850 lm，强度插值避免突变，保留相机至发射口遮挡与起点穿透关闭逻辑。build.log 构建成功；未启动游戏或验收渲染，请重启编辑器后自行测试。

## 尾部金属材质（用户确认接入成功后的修订）

按用户要求取消手电尾部原生成红色材质。fix_flashlight_tail.py 基于三枪当前主体材质创建 MetalTail 变体，以局部空间位置将前端光学区之外的区域全部使用同一金属涂层，保持对应 BaseColor/Roughness/Metallic/Specular 与原法线。运行装配入口覆盖 M_Tactical_flashlight 材质槽，原模型和光照参数保留。材质保存记录 metal_tail.log；未进行游戏测试。
