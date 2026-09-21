# 陨星主体改用现有写实资产 · 2026-09-21

后续火焰已切换 Free Spline VFX 的 SplineV4，记录见 [火系火焰替换](fire-magic-spline-vfx-20260921.md)；本文所述写实岩体和材质继续使用。

用户反馈 V2 陨石卡通感明显，要求查看现有材质资产并使用写实资产。V2 并非从零原创建模：源为 EasyBuildingSystem 的 Stylized/SM_SmallRock_001，经过重新分布网格和噪声处理，表面采用自制程序熔裂纹。这套风格化来源与规则高亮裂纹不适合此次目标。

## 素材选择

读取本机三类候选的模型比例、配套材质和纹理。Rural Australia 的 Rock_M_02 有配套 2K 颜色/粗糙度、法线以及细节法线材质；Niagara Examples 的 S_Rock_shopk 为 150 三角形的小石块，Military Trench 对比的 Scatter_Rock_S_04 是约 13cm、256 像素底色的小碎石。选用 Rural Australia Rock_M_02，避免将低分辨率散落物放大为主视觉。

- 来源模型：`/Game/RuralAustralia/StaticMeshes/Rocks/Rock_M_02/SM_Rock_M_02`。
- 来源实例：同目录 `MI_Rock_M_02`，母材质 `/Game/RuralAustralia/Presets/M_Nature_01`。
- `T_Rock_M_02_CA` 的 RGB 是底色，A 通道在原图中接粗糙度；`T_Rock_M_02_NA` 接法线。通道按实际原材质读取，没有套用通用 ORM 假设。

## 制作与接入

新资产在 `/Game/Skills/FireMagic20260921/RealisticV3`：

- `SM_MeteorNaturalRock`：原模型的独立副本，仅居中枢轴及统一缩放；保留 1091 三角形的天然轮廓、UV 和法线，不再使用风格化岩体或程序噪声重塑。作者最长边 76cm，现有运行逻辑将最长边设为 80cm。
- `M_MeteorNaturalRock`、`MI_MeteorNaturalRock`：完整复制来源材质图和实例，保留原有粗糙度、法线、细节法线和 UV。在最终材质属性上仅对底色做适度去饱和与 0.52 亮度烧黑，微细节平铺调为 18。关闭原本已关闭的风、世界投影、覆盖层和岩石污渍开关，纹理随岩体旋转。
- 取消程序蜂窝/熔裂纹和岩体自发光；燃烧由现有 V2 贴体火、尾焰、落地爆燃和余火表现。碎片复用新的写实岩体与材质。
- `FPSMeteorStrike.cpp` 及 `FPSFireMagicComponent.cpp` 的加载/预载引用同步切到 V3。伤害、坠落时长、范围、姿态与其他技能没有调整。

恢复入口 `Tools/Skills/build_meteor_realistic.py`，通过现有 MCP 桥依次执行 `run('material')` 和 `run('mesh')`。完整图/实例副本与网格均已制作保存；恢复需保留 RuralAustralia 的材质函数、主纹理和细节纹理依赖。旧 V2 资源继续保留历史恢复用途。

## 执行边界

素材读取曾因强制 PNG 导出 HDR 源纹理触发 UE 的 SupportsTexture 断言退出，当时未进行资产修改。之后改用 UE 自动选择支持源格式的导出器并完成素材读取。

本轮仅读取素材、制作并保存资产和执行必要代码编译；未启动 PIE、未进行效果截图、预览渲染或游戏测试。新效果由用户实机判断。构建方式另见本目录制作记录。

本轮使用 `LiveCoding.CompileSync` 完成资源路径改动的必要编译，补丁创建日志返回 successful / Finished，记录 `SourceAssets/MeteorRealistic20260921/live-coding-result.txt`。编辑器仍有工坊材质未保存，本任务没有保存或关闭这些内容；当前接入使用热补丁，基础 Editor DLL 的常规构建尚未进行，不能将本轮状态当作重启后的基础模块已更新。
