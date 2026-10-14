# 篝火接入 Free Torch Fire（2026-10-13）

正式项目：`D:/FPS3D/FPSGAME`。仅调整篝火表现，不改木工台。

## 已保存内容

- 正式 Niagara：`/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire`。
- 专用材质：同目录 `M_CampfireTorchFire`、`M_CampfireTorchSmoke`。
- 制作来源：本机已导入 `/Game/TorchFire/FX/NS_TorchFire_Standard`，CodePhase Games 的 [Free Torch Fire](https://www.fab.com/listings/7437ae0c-d67c-4f0a-af81-d03774cfdb82)。本次未购买或下载。
- 正式引用：`Source/FPSGAME/Building/ColdSteelCampfire.cpp` 构造函数。该文件只替换一个资产路径字符串。
- 旧系统 `/Game/Building/Campfire20261012/Realistic/NS_CampfireRealisticFlame` 与厂商原件保留；安装前后哈希一致。

## 尺寸与参数依据

读取当前 `SM_Stylized_Campfire` 的 LOD0 顶点与连通片，而非使用旧文档估计。石圈整体约 86.40 × 89.00 × 39.49 cm；内侧木柴连通片的 XY 联合边界约 49.88 × 51.51 cm。模型经现有构造函数归中、落地后，内侧木柴高度约 9–39.5 cm。

Niagara 组件仍在 Actor 局部 `(0,0,20)`，缩放 `(1,1,1)`。保留原 8×8 火焰／烟动画和原贴图比例，调整粒子出生分布及运动，不把整个火炬压扁。

| 层 | 生成率 / s | 寿命 / s | 出生尺寸 / cm | 出生分布与运动 |
|---|---:|---:|---|---|
| Fire | 12 | 1.10–1.55 | 正方形贴片 62–76 | 半径 14 cm 圆盘；贴片底部起于组件原点；向上 10–16 cm/s |
| Smoke | 1.4 | 2.3–3.0 | 35–45，保留原生尺寸曲线并封顶 72 | 半径 12 cm；局部 Z=45；向上 22 cm/s，加速度 Z=3，阻力 0.15；初始 alpha 0.15 |
| Sparks | 2.5 | 1.1–1.7 | 1.1–1.8 | 半径 18 cm；局部 Z=10；向上 35–52 cm/s，横向 5 cm/s；curl 强度 3.5，阻力 0.35 |

火焰贴片的几何上界约为 Actor Z=121 cm；透明贴图中的实际可见火舌范围须由用户实机确认，不能将贴片尺寸当作已测可见焰高。烟的尺寸封顶用于约束透明覆盖及包围盒。

三层保留局部空间与原 GPU 模拟路线。系统及发射器采用固定包围盒，局部 min `(-115,-115,-15)`、max `(115,115,225)` cm，系统固定包围盒开关已开启。保留原生色彩、SubUV 动画、火焰侵蚀；移除朝相机偏移、原出生位置／速度模块，用独立尺寸合同替代。

原火焰／烟材质的 DepthFade 为 75／150 cm。本次只在复制材质中改为 4／8 cm，并显式连接常量到淡出距离输入；原透明度与颜色链保留，厂商材质不改。

## 保持的运行合同

移除副本中的 `Light001` 和第二层 `Sparks001`。每个系统只含 Fire、Smoke、Sparks 三个 sprite renderer，无 Niagara light renderer；继续使用现有 350 lm 无阴影点光源。稳态粒子数量保守估算约 32 个／系统（含生成边界余量），不是性能实测。

`FluidPresentationSubsystem` 的最多 8 处篝火、30 m 进入／35 m 保留、0.2 s 共享调度保持不变。点火／熄灭、燃料、温暖范围与数值、网络、烹饪、声音／伤害及存档路径均未改动；仍使用一个 Flame 组件，熄灭立即销毁表现。木工台无本次修改。

## 制作与验证

资产在独立临时宿主制作；它没有游戏模块或运行世界。本机正式 Editor DLL 缺失且当时工程编译有其他文件错误，因此没有为资产制作修改这些文件。

- 新包已实际保存，再由新的 commandlet 从磁盘重新加载。
- Niagara 返回 `valid=1`，无待完成 Niagara 编译；三层结构、出生参数、局部空间、包围盒开关与新材质引用均读回。
- 八个 `/Game` 资产依赖均存在；无临时宿主 `CampfireAssetTools` 运行依赖。
- 新包安装使用唯一目录，源码安装使用 SHA-256 冲突保护；27 份相关旧文件备份保留。
- 使用 NullRHI 进行图表编译及包依赖读取；没有 GPU 画面／着色器渲染验收，没有启动游戏、PIE 或 GUI 编辑器，没有写真实存档。不得将这些静态结果表述为视觉或性能验收。
- Editor/Game 必要构建状态与最终阻塞以 `SourceAssets/Campfire20261013/TorchFire/delivery.json` 为准。

证据与重建源均在 `SourceAssets/Campfire20261013/TorchFire/`：`final-asset-readback.json`、`material-adaptation.json`、`mesh-islands.json`、`install-receipt.json`、`baseline-sha256.json`。重建在空的同名目标目录依次运行 `author_torch_campfire.py`、`adapt_materials.py`；现有资产不盲目覆盖。脚本可使用正式工程的 RainAssetEditor，临时宿主使用等价的独立工具类。

## 回退

只将 `ColdSteelCampfire.cpp` 中新的完整对象路径换回 `/Game/Building/Campfire20261012/Realistic/NS_CampfireRealisticFlame.NS_CampfireRealisticFlame`，然后完成对应 Editor/Game 构建。旧包仍在原位，不需要恢复或删除厂商素材。`Before/` 保存安装前源码及相关二进制；若源码后来继续变化，只恢复本次路径，勿整文件覆盖他人改动。
