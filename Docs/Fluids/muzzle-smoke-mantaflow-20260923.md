# Mantaflow 枪口烟 V14

2026-09-23：已制作、导入、保存并接入枪口烟，完成 FPSGAMEEditor 后台构建。没有启动编辑器界面、PIE、游戏或验收渲染；视觉质量与实际帧率由用户测试。

## 本次改动

- 新制三股短脉冲 Mantaflow 烟雾源，96³ 固定网格，64 帧 OpenVDB 缓存；可编辑源保存在 `SourceAssets/MuzzleSmokeMantaflow20260923/MuzzleSmokeMantaflowV14.blend`。
- 沿 Y 轴积分密度，按每帧烟团重心和范围裁取；输出 2048×2048、8×8 排列、每格 256 像素的线性密度贴图。每格留 4 像素透明边缘。该步骤直接处理模拟密度，没有运行相机预览或验收渲染。
- 烟片按粒子自身年龄播放 64 帧，线性混合相邻帧，最后一帧不回卷。纹理使用 Masks 压缩、关闭 sRGB 和 mipmap，避免动画格之间串色。
- 材质沿用 V12 的光照、ParticleColor 透明度、深度交界柔化和老烟瞄准区淡化，只替换密度生成部分。
- Niagara 沿用 V12 世界坐标连续烟流、生命周期及透明度曲线。现有每秒发射数量、热量、停火余烟、枪口定位、ADS/瞄具逻辑及消音器分支的代码不变。
- 运行引用和异步预加载清单已切到 V14；旧 V12 资产保留。枪口火光仍用 V10。

## 已保存资产

均在 `/Game/Weapons/GunplayFX`：

| 资产 | 用途 |
| --- | --- |
| `T_MuzzleSmokeMantaflowV14` | 原创模拟密度动画图集 |
| `M_MuzzleSmokeMantaflowV14` | 相邻帧插值和现有烟雾材质处理 |
| `NS_FPS_MuzzleSmokeMantaflowV14` | 当前枪口烟运行资产 |

运行时仍是 Niagara 烟片，没有逐枪三维流体求解，也没有把整个 VDB/SVT 序列加载为枪口体积。帧率和显存变化没有实测，不能将完成制作等同于性能或视觉验收通过。

## 制作与接入入口

- `Tools/Fluids/bake_muzzle_smoke.py`：Blender 后台模拟、VDB 缓存和密度投影。`--export-only` 可从已保存模拟缓存重新输出贴图。
- `Tools/Fluids/author_muzzle_smoke_ue.py`：UE 后台导入、材质/Niagara 制作和指定资产保存。
- `SourceAssets/MuzzleSmokeMantaflow20260923/MuzzleSmokeFlipbookV14.hlsl`：动画贴图采样代码。
- `Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp`：正式枪口烟加载路径。
- `Source/FPSGAME/Characters/FPSPreloadAssetRegistry.gen.h`：同步更新该单条预加载路径。

## 制作记录

- Blender 已完成真实流体烘焙和 PNG 导出；见源目录 `bake.log`、`bake-manifest.json`。
- UE 已保存三个资产并执行材质/Niagara 编译调用；见 `ue-assets.json` 和 `ue-authoring.log`。
- 本次 UE commandlet 因 MCP HTTP 监听器的 `127.0.0.1:8000` 端口被占用而返回退出码 1；脚本自身已执行到 `MUZZLE_MANTAFLOW_AUTHORING_COMPLETE` 并保存资产，未停止占用端口的进程。此退出码不能记作完整 commandlet 成功。
- 常规 Editor C++ 构建 `Result: Succeeded`，日志 `Saved/BuildEditor/build-20260923-213330.log`；重编译了枪械 FX 与预加载模块并链接 `UnrealEditor-FPSGAME.dll`。
- 没有自动运行测试、截图、预览或验收。

## 可见度调节

用户反馈烟雾不明显后，增加了材质密度增益：初生阶段为原来的 1.35 倍，随粒子年龄在 15%～70% 区间平滑过渡为 1.15 倍。保留烟雾形态、发射数量、尺寸、生命周期和原有瞄准区淡化；未运行游戏或进行视觉验收。

入口为 `Tools/Fluids/tune_muzzle_smoke_visibility.py`，仅从原始 HLSL 更新并保存当前 V14 材质。原制作脚本读取同一份 HLSL，重新制作会保留此次参数。执行记录为源目录的 `visibility-tuning.json`。

## 来源

烟雾模拟与密度贴图为本项目原创制作；Niagara 和材质从本项目现有 V12 枪口烟派生，沿用现有来源许可。本次没有新增付费插件或第三方下载素材。

[Epic 官方 Niagara Flipbook Baker 文档](https://dev.epicgames.com/documentation/unreal-engine/niagara-flipbook-baker-quick-start-guide-in-unreal-engine)说明了把流体模拟烘焙成动画贴图、再用于烟片的实现思路。本次使用 Blender 后台模拟及密度投影完成贴图制作；相关 API 见 [Blender FluidDomainSettings](https://docs.blender.org/api/main/bpy.types.FluidDomainSettings.html)。
