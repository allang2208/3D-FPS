# 陨星与灼锋焰甲：流体燃烧层次

2026-09-23，按用户要求将火球燃烧场方案推广到陨星和灼锋焰甲。已增量制作并保存四个当前材质，覆盖两项魔法的六个现用 Niagara 系统。没有启动编辑器界面、PIE、游戏、截图或验收渲染。

## 各部位适配

| 部位 | 现用材质 | 燃烧场处理 |
| --- | --- | --- |
| 武器小火、脚边火环及地面低火 | `M_NaturalBladeFlame` | 14 帧/秒基础推进，细节混合 0.55，较缓的冷热变化 |
| 武器翻卷火、运动余焰、尾焰及火场 | `M_NaturalRollingFlame` | 18 帧/秒基础推进，细节混合 0.72 |
| 陨星包覆火与分离火舌 | `M_NaturalMeteorFlame` | 23 帧/秒基础推进，细节混合 0.78，较快翻卷 |
| 落地爆燃 | `M_NaturalImpact` | 按粒子归一化寿命播放 0～63 帧，细节混合 0.62，不循环 |

循环层另按粒子年龄错开相位，避免同一火场同步明灭。使用 R 火焰强度、G 温度、B 烟密度调节原火焰发光中的冷热颜色与柔和明暗，保留原火焰序列的轮廓、纹理解码、透明度和 Dynamic Parameter 语义。

四个材质均位于 `/Game/Skills/FireMagic20260921/RealisticV5`。它们由 `NS_ArmorNaturalFire`、`NS_ArmorNaturalAura`、`NS_MeteorNaturalMantle`、`NS_MeteorNaturalWake`、`NS_MeteorNaturalImpact`、`NS_MeteorNaturalAfterfire` 使用，运行引用不需要改动。

## 数据与材质连接

共用火球已制作的 `/Game/Skills/Fireball/FluidCore20260923/T_FireballCombustionFields`：原创 Mantaflow 模拟、2048×2048、64 帧线性 RGB 数据。本轮未增加纹理资产或重新烘焙；原始制作见 [火球流体内核](fireball-fluid-core-20260923.md)。

Niagara sprite 的 UV0 已带原生 SubUV 变换，因此先按各材质 8×4、6×6 或 12×12 网格恢复格内 UV，再采样独立的 8×8 燃烧场。相邻燃烧帧插值；没有把原包贴图尺寸强改为 8×8。

热度变化插在原发光输出与 `EyeAdaptationInverse` 之间。原曝光补偿仍保持唯一一层，原透明度、DepthFade 与预乘连接保持。烟材质、写实岩体和当前火球材质未修改。

本轮增加的是每个火焰材质对共用贴图的两次采样；没有增加粒子发射数量、灯光或运行时三维流体模拟。伤害、灼烧、持续时间、碰撞、冷却、消耗、修炼、施法手势与实际武器端点定位均未改。性能没有实测。

## 制作与恢复

- 作者脚本：`Tools/Fluids/apply_fire_magic_fluid_fields.py`。
- HLSL：`SourceAssets/FireMagicFluidFields20260923/CombustionDetail.hlsl`。
- 原作者 `Tools/Skills/build_fire_magic_realistic.py` 的 `materials()` 已追加安装函数，后续完整重建保留本轮燃烧场处理。
- 首次修改前的四个材质备份保存在源目录 `Before`，路径与 SHA-256 记录在 `delivery.json`。
- 后台 `UnrealEditor-Cmd -run=pythonscript -NullRHI` 完成，退出码 0；四个材质已保存，重编译 API 无即时错误。日志为源目录 `ue-authoring.log` 与 `ue-stdout.log`。
- 本轮没有 C++ 改动；NullRHI 制作完成不等于 SM6 实机着色器和画面验收，实际表现由用户测试。

新燃烧场为项目原创。Realistic Vol.2 与 Military Trench 的原材质及图集继续沿用原许可；第三方母版没有改动。
