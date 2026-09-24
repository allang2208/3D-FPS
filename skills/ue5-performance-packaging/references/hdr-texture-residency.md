# HDR 常驻开销与间歇性纹理低清

用于天空立方贴图占用异常，或持枪贴图偶发模糊的排查。沿用用户的后台制作与按需测试规则；读取本文不自动授权运行游戏、采样或改变画质。

## 先分清纹理数据、流送池和总显存

- 立方贴图有六个面。按实际驻留尺寸、格式和 mip 数计算，不能把 equirectangular 原图宽高、uasset 磁盘大小直接当显存。
- 单层立方贴图数据为 `6 × 面宽 × 面高 × 每像素字节数`。FloatRGBA 为 8 字节；BC6H 的 4×4 块为 16 字节，4K/2K 这类整块尺寸等效每像素 1 字节。完整 mip 链约为单层的 4/3，已有 NoMipmaps 时不能擅自算入。
- 非流送 HDR、纹理流送池、捕获资源和整卡显存口径不同。不要从剩余流送预算中再直接扣减一遍 HDR 数据，也不要由某张恢复后的快照推定故障时超预算。
- 格式与尺寸得到的是纹理数据估算；资产构建、保存回执、实际运行驻留、帧时间和视觉观感分别报告。

## 保持分辨率的 HDR 压缩制作

对支持 BC6H、无需 alpha 的线性 HDR 天空，可先保留分辨率改用 `TC_HDR_COMPRESSED`，再根据用户观感决定是否降分辨率或调整加载策略。BC6H 有损，不能承诺高亮边缘、暗部与渐变逐像素不变。保留源数据、sRGB=false、原 mip/LOD/MaxTextureSize 和亮度调节；压缩不应顺带改曝光、Lumen、光追或纹理池。

FPSGAME 制作入口为 `Tools/Weather/compress_sky_hdr_bc6h.py`：检查目标未保存冲突、精确备份、改格式、等待编码完成、只保存目标纹理并记录前后属性。现有编辑器使用项目互斥桥；编辑器关闭时按支持情况使用无界面 commandlet，不为这一步启动交互编辑器。`Editor.AsyncAssetCompilationFinishAll` 会等待资产编译，属于制作操作，不是零扰动诊断命令。

UE 5.8.2 Python 中 `compression_none` 不存在，原生 `CompressionNone` 又受保护；不要反复改属性拼写或把失败读取默认为 false。本例改可写的 `compression_settings`，以实际构建格式 `TFO_BC6H` 和保存回执记录结果。仅写脚本、仅返回 RPC success 或设置枚举，不等于资产已经编码落盘。

本例六张 4K 加一张 2K、均单层：4800 MiB → 600 MiB，理论减少 4200 MiB（87.5%）。这是 2026-09-24 已保存制作的格式估算，没有做压缩后性能／观感复测，也没有证明它修复了 M4 的偶发低清。工程记录：`Docs/Performance/sky-hdr-bc6h-20260924.md`。

## 低清现场与诊断动作的影响

1. 先区分实际第一人称网格、枪匠预览与物品图标。图标日志 `reason=TextureStreaming` 不能直接证明持枪贴图正在缺 mip；读实际组件和运行材质引用。
2. 用户明确要求现场排查时，尽量先记录 resident/requested/wanted mip、pending 状态、时间戳和池预算，再运行可能推进流送的命令。
3. 本机 UE 5.8.2 的 `ListTextures -CSV` 在列出纹理前调用 `UpdateResourceStreaming(0.f, true)`，会同步推进流送调度。相关实现位于 `Engine/Source/Runtime/Engine/Private/UnrealEngine.cpp`。不能把该命令当作完全被动读取；用户随后恢复不等于已找到原因或完成修复。
4. 无 RHI 或尚未有编译资源的 commandlet 中，已编译材质纹理列表可能为空；继续依据资产注册表依赖区分“没有编译资源”和“引用丢失”。
5. 棋盘格材质、采样器类型不匹配、空材质槽、粗糙度误开 sRGB 和流送低清是不同问题。分别记录证据，不用统一的纹理池扩容掩盖原因。

源码里存在短时驻留策略不代表当前手持武器在使用它；永久强制所有资源驻留也不是现场诊断的默认动作。天空高亮方向问题转到天气技能的 `references/sky-highlight-attribution.md`。
