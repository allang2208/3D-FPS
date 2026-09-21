# A762 瞄具材质统一补齐

用户要求检查瞄具是否统一材质后继续制作。本轮只处理全息、全景红点、2×棱镜、1–6× LPVO 和独立倍率环。

检查发现：Accessories05 实际材质绑定正确，但在 M4 接收器涂层图外再次用转换后的金属度生成遮罩。该遮罩不等同于原始金属区域、白色刻字保护与镜筒内壁排除遮罩；Specular 仍保留 M4 Phong 转换，粗糙度也只有常数。

已复制原瞄具材质图，在原涂层混合节点中直接替换金属分支，移除 M4 颜色／粗糙度采样和 Phong 转换。以当前运行上机匣 `M_A762_UpperReceiver03` 为基准：线性底色 (0.021, 0.028, 0.040)、金属度 0.83、粗糙度中心 0.34、微变化幅度 0.018、Specular 0.5。使用同一机匣细纹贴图，独立 UV2 的物理平铺为 5×5 cm；不把机匣零件图集套到瞄具。

保留原 UV0、结构法线、AO、白色刻字、橡胶／聚合物分区、镜筒消光内壁、透明／裁切、镜片和分划。棱镜／LPVO／倍率环沿用源顶点 R 内壁遮罩。全息源材质原本没有 Normal 输出，本轮不额外虚构法线。

实际运行网格继续位于 `/Game/Weapons/A762/Accessories05/Meshes`，只有外壳槽更新到 `/Game/Weapons/A762/OpticFinish06/Materials`。几何、安装位置、ADS 光心、倍率环轴和游戏数值不变。修改前网格在 `OpticFinish06/Before`，可回退到其材质绑定；共享 M4 材质未修改。

作者入口：`apply_finish.py`；原始检查：`before.json`、`source_masks.json`；保存回执：`installed.json`；按用户要求的材质绑定与图连接检查：`after.json`、`checked.json`。后续 Accessories05 重导入会使用 `finish_overrides.json` 保留此次材质。

本轮只修改材质资产和导入脚本，无须 C++ 编译。未启动 PIE、渲染或进行游戏测试，视觉与实际操作由用户测试。
