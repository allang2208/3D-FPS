# 悬钟背膜展开修订 V09

2026-10-04。按用户最新要求，三叠鸣震恢复 V06 的上、中、下三层依次展开，以及左右轻微错时；仅开膜段加速至原来的 1.5 倍。此要求替代 V07 的三层同时在 0.12 秒内展开。

以原展开起止时间除以 1.5 烘焙曲线，每片开膜耗时由 0.52 秒缩至约 0.347 秒。左侧上、中、下层分别在 0.400、0.547、0.693 秒全开；右侧保留约 0.017 秒错时，全部展开约 0.710 秒。保持原展开方向、弧度、幅度和四节连续骨链。

动画仍为 5.6 秒、60 FPS、337 个采样，RateScale 为 1。六次压缩/弹震与命中仍在 1.10、1.80、2.50、3.20、3.90、4.60 秒，收拢和身体动作保留 V07。伤害、20 米范围、每次有效命中扣 2 SAN、音效、柔边声波及 V08 群眼凝视不变。

制作源与 FBX 在 `SourceAssets/HangingBellM09Meshy20261003/ResonanceOpeningV09/`，作者脚本为 `Tools/HangingBellM09/author_resonance_opening_v09.py`。修改前动画包备份在 `Records/Before/`。

通过现有编辑器桥结束正在运行的 PIE 后，实际重导并保存原运行路径 `/Game/Monsters/HangingBellM09/V07/Animations/A_M09_Resonance_V07`。不改 C++ 或正式引用，因此不需要原生构建或重启编辑器。保存回执见 `Records/import_saved.json` 和 `Records/import_bridge_02.txt`。

没有启动游戏、PIE、预览、截图、渲染或测试，由用户重新触发三叠鸣震体验。
