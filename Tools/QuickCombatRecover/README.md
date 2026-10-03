# 快速近战 recover 段诊断脚本（2026-09-19）

用于量「快速近战/近战收势时手臂复位突然形变」这一类问题。全部只读：加载 UE 资产采样姿态、
输出 JSON 到 `Saved/QuickCombatRecover/`，不改任何资产。

口径统一：**按臂骨量 480 Hz 逐帧角增量（deg/frame；×480 = deg/s）**，同时看 armature 空间
（整臂读数）与父级相对空间（关节台阶）。缺陷签名是"先减速到 ~0.1°/帧 → 突然回到 2.0°/帧 →
硬停"，只在 clip 首末帧出现。

| 脚本 | 用途 |
| --- | --- |
| `measure_recover_tail.py` | 各 clip 末帧 vs 运行时 idle 的逐骨姿态差 + 末段速度 |
| `profile_recover.py` | 整段密采样速度剖面，找跳变点 |
| `comp_fixed.py` | 组件空间逐帧角速度（修正合成顺序后的版本） |
| `elbow_tail.py` | 肘弯曲角/方位角/前臂长度的末段轨迹（判"肘面翻转"类形变） |
| `pistol_tail_check.py` | 手枪(715/1911)与 M4 步枪同类收音段的逐帧检查 |
| `v47_tail_detail.py` | 已修复版（V47）尾部逐帧复核 |
| `definitive.py` / `exact_tail.py` / `gap_to_end.py` | 早期一次性测量（保留作对照） |
| `arm_chain.py` / `tail_kinematics.py` / `raw_tail.py` / `final_tail_compare.py` | 早期迭代版本（合成顺序或单位曾写错，已废弃但留档） |
| `blender_tail_probe.py` | 在作者源 blend 里量同一段（判缺陷来自作者源还是导入） |
| `probe_api.py` / `probe_vec.py` / `asset_rate.py` | UE Python API 探针（AnimationLibrary、Vector、资产帧率） |

作者源侧的解算器修复、参数扫描与验收脚本在
`SourceAssets/MeleePommelAttack20260916/`（`validate_recover_fix.py`、`release_window_final.py`、
`verify_recover_fix.py`、`readback_ue.py` + `run_readback.ps1`，一次性探针在 `Probes20260919/`）。
案例结论见 `Docs/Weapons/runesword-pommel-strike-20260916.md` 的「收势手臂复位修订 V47」节。

运行（编辑器开启时）：

```bash
python Tools/AssetPipeline/ue_python_exec.py --script Tools/QuickCombatRecover/pistol_tail_check.py
```

编辑器关闭时：这些脚本依赖 `unreal` 模块，走 `-run=pythonscript` 的 ImportHost 通道
（参考 `SourceAssets/MeleePommelAttack20260916/run_readback.ps1` 的写法）。