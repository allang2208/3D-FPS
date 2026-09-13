# 高性能后托 Meshy 替换

源压缩包与散列见 provenance.json，Source 内保留原始 FBX 和贴图。用户选择的模型替换 qr_performance；三枪显示名称均改为“高性能后托”，保留 ID、数值和存档合同。

## 制作与接入

- 原模型573816三角面，保留网格和顶点法线、不减面或重新平滑。原UV0用于源结构法线及聚合物贴图，独立UV1用于枪体涂层。
- 按短端开口管的前缘与上部圆管中心确定安装轴，统一主体长度18cm。M4前缘在现有安装坐标中为+7mm，AKM为+2.8mm，保持原角色StockMount。AKM保留带管道通孔的机匣连接座；QBZ沿用机匣尾部的专用肩台与连接座位置，网格预变换到其WPN_root坐标。具体参数见author.py和authoring.json。
- 材质按源金属度图分区，末端肩垫单独分为橡胶。金属匹配M4现用Phong转换、AKM机匣PBR区域、QBZ现用涂层；聚合物使用源颜色/粗糙度/法线，肩垫粗糙度下限.75。新连接座不采样无关的源模型结构法线。源emission未用于自行添加发光效果。
- UE正式材质由import_assets.py生成；Blender编辑源中的金属是近似工作材质，不代表UE最终涂层。
- 导入路径 /Game/Weapons/QRPerformanceStock/Meshy20260913/{M4,AKM,QBZ191}/SM_PerformanceStock，已有QRPerformanceStock打包目录覆盖新路径。
- SkeletonStockVisual.cpp及QBZ191Attachments.h切换共用装配入口；gunsmith.json三条显示名称同步更新。修改前精确文件保存在Before，旧引擎资产保留。
- 各枪子目录提供可编辑blend与FBX；author.py/import_assets.py为制作入口。

## 交付边界

完成制作、导入和必要原生编译；未启动游戏、未做本轮装配/材质/动画验收。meshy_clay.png仅为制作前识别源连接端的参考视图，不是接入预览。用户重启编辑器后测试各枪连接位置与材质。原模型约57.4万面，未进行性能优化或测试。
