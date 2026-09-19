# ASH-12 30 发扩容弹匣（2026-09-19）

来源：本机已接入的 ASH12Surface20260919/ASH12_Surface_Editable.blend，沿用原 ASH-12 资产的授权与分发限制。

- 原厂 20 发改为 30 发，mag_delta=10、reload_mult=1.25、ads_percent=0.05。
- 从原厂前后轮廓拟合共同曲率中心，在抓握区下方插入 75 mm 曲面延长段；上部插接段与抓握截面不动，下部原壳和独立底板沿弧线刚性移动。
- UV 使用本枪中段表面，接缝以 4 mm 半宽混合原 PBR 通道；替代采样法线转换到当前切线系。干湿材质都保留同一规则；独立底板仍使用原厂材质及其天气映射。
- 模型以枪体网格坐标导出，运行时用原厂 WPN_SOCKET_Magazine 绑定逆矩阵定位，跟随 ASH 现有普通/空仓换弹。
- 专属图标 ue_ash12_magazine_ext_mag，前方朝左、上方朝上，水平正交侧视、1024 RGBA；真实模型制作，不做二维镜像。

制作入口：measure_source.py、measure_sections.py 为制作尺寸提取；author.py 为模型/UV 作者脚本；install.py 导入 UE 模型与材质；render.py 制作产品图标；install_icon.py 接入图标。

可编辑模型：ASH12_ExtMag30_Editable.blend；导出：SM_ASH12_ExtMag30.fbx。
引擎目录：/Game/Weapons/ASH12/ExtendedMagazine20260919。

完成制作、导入、接入与必要构建；未进行游戏测试、换弹抓握验收或额外预览。最终外观和实机行为交由用户测试。

必要构建同时修复了 Building/VoxelBuildWidget.cpp 的编译阻塞：USizeBox 对齐属性应写入 USizeBoxSlot；仅修正 API 调用归属，保留布局值。
