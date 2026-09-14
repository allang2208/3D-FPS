# 715 官方 Chromium 材质接入

用户已将 Epic Automotive Substrate Materials 下载到项目。本次使用实际 `MI_Chromium` 预设及其母材质，给现有 715 换为干净的镀铬银色表面。保留 Detail 版本的几何、UV0、切线、蒙皮、刻字和沟槽法线；不使用已撤回的 Precision 重建网格。

## 来源与作者文件

- [Fab 官方资源](https://www.fab.com/listings/1272587c-1431-4878-9d78-2a6b84ebe839)：Epic Automotive Substrate Materials。
- 本机源：`Content/SubstrateMaterials/Materials/03_Metals/1_Basic/MI_Chromium.uasset`。
- 源父链：`MI_Chromium → MTP_Metal → M_Metallic`。
- 作者入口：`SourceAssets/DanWesson715Chrome20260914/import_chrome.py`。
- 来源图与参数记录：同目录 `source-material.json`；资产写入记录：`import.json`。
- 原包和派生二进制留在本机，保留 Fab 原包许可。此记录不授予源素材再分发许可。

## 材质处理

枪身使用复制的 Epic `M_Metallic` 和 `MFW_Aniso_BaseMetal`，保留原生 Substrate Slab BSDF、金属 F0/F90 和反射计算。实例复制官方 Chromium 及其模板的有效参数后再改父级，避免丢失继承覆盖。

官方预设的砂喷法线、磨损粗糙度和三向投射不直接用于枪械：法线改为 Detail 的三张 4K 结构法线，使用原 UV0，强度 1；沿用贴图导入时的绿通道转换，材质不再翻转。关闭附加指纹、灰尘、划痕、薄膜、发光及调试叠加。

金属颜色使用 Chromium 的实测预设值 `(0.6428, 0.6512, 0.6616)`，A/B 统一为该颜色，避免表面颜色噪声。局部 AO 单独接入，不烘入金属底色。

| 区域 | 基础粗糙度 | 处理 |
|---|---:|---|
| 枪架与护罩 | 0.025 | 清晰抛光面 |
| 弹仓 | 0.020 | 较亮的圆柱高光 |
| 扳机、击锤和小钢件 | 0.034 | 略收敛反射以区分机械件 |
| 配件金属外壳与底座 | 0.030 | 匹配枪身的干净镀铬表面 |

主体局部粗糙度沿用 Detail ORM 中高于旧基准的结构差异，幅度为 0.35，不叠加全枪颗粒。以上是制作参数，不代表已达到用户的视觉预期。

四种配件复制现用 Mirror 网格，保持大小、挂点、光心和材质槽顺序。七类配件材质的金属分支使用官方 `MFW_Metallic_BaseMetal_Color` 与同一 Chromium 参数，保留原有混合区域遮罩及光学材质管线。配件不是整件强制替换为不透明金属；镜片、分划、非金属区及发光遮罩继续使用原有输入。

## 雨滴与运行入口

- 主体：`/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny`。
- 配件：`/Game/Weapons/DanWesson715/Chrome20260914/Attachments`。
- 雨滴：`/Game/Weapons/DanWesson715/Chrome20260914/DA_DW715_WetMaterials`。
- C++ 统一入口：`Source/FPSGAME/Weapons/DanWesson715WeaponAssets.h`。

主体雨滴直接接入复制的原生 Substrate Slab 的 Normal/Roughness。使用现有 `WeaponBeads.hlsl` 和 `WeaponWetness`，保持 UV0 随蒙皮运动。晴天值为 0；天气组件创建湿材质 MID 后继续控制积水与干燥。配件保留对应的干湿母材质与实例。10 组新增映射通过本枪独立表合并，无需覆盖已打开的公共天气资源。

现有 `/Game/Weapons/DanWesson715` Cook 目录包含新资源；下载包的实际母材质、函数、纹理及 BaseMaterial 插件函数由材质硬引用保留。没有改变全局 Substrate、反射、曝光或光照设置。

逐发/速装换弹、左右手动画、开火等待、录音、改造尺寸、准星和存档沿用当前实现。回退表面只需将同一头文件的主体/雨滴恢复到 Detail、配件恢复到 Mirror，原资产仍在。

## 交付状态

已制作并保存材质、实例、主体和配件副本及天气映射，并接入统一加载路径。必要的 FPSGAMEEditor Win64 Development 构建完成，UBT 返回 0、`Result: Succeeded`，模块后缀 `71417`，用时 73.49 秒；日志在作者目录 `build.log`。未运行游戏、渲染或额外测试，由用户重启编辑器后自行查看效果。

材质作者命令使用 NullRHI。项目已有的 GameFeatureData 资产管理配置错误会使 commandlet 最终返回 1；本轮资产制作是否完成以 Python 执行结果、成功保存和 `DW715_CHROME_IMPORT_COMPLETE` 为准，不将这一退出码描述为测试通过。
