# 推掌 V5：腕部与前臂修正

历史版本：用户随后反馈小臂仍有轻微扭曲、收手僵硬，当前修订见 `../RecoveryV6/README.md`。本目录的 Blend、FBX 与检查结果保留，不由当前 V6 作者脚本覆盖。

用户反馈 V4 腕部扭曲、前臂有错误拉伸观感，并明确要求检查对比参考图。本目录保存该次修正的可编辑模型、九段 FBX、参考照片及局部姿态检查。

作者入口：`../../FireballCast20260914/author_cast.py`；读取当前 `Content/ColdSteelData/Skills/fireball_hand_pose.json` 与 C++ 时钟，输出到本目录。母版继续使用 `GASPTraversal20260910/Native/TraversalArms_Editable.blend`。运行时由 `FPSCastingMeshComponent` 求解，FBX 不替换武器动画。

改动：腕部前伸从 50 cm 收到 44 cm；肘部 pole 从外侧移至手掌下方，肩部前送同步减少；手指略向前倾，使手背、手腕和前臂更连续。前臂通过掌宽轴投影确定 roll，手腕的背屈不再混入整条前臂的 twist。主骨与辅助骨仍使用完整骨段变换，骨长与缩放不变。推掌到位后固定停顿 0.30 秒再 recover。

检查脚本：`../inspect_wrist.py`。`BeforeNeutral/` 和 `After/` 使用相同相机、灯光与中性材质，输出正面／侧面源模型渲染以及约 60 Hz 的整段姿态测量。终点腕臂轴夹角 V4 为约 63.07°，V5 为约 26.42°；沿前臂轴计算的腕部额外扭转从约 13.59° 降至 0°。这些是三维源模型测量，不能当作参考照片的三维角度或 UE 实机验收。

`reference-description.txt`、`after-description.txt` 保留项目 DeepSeek 读图通道的返回；该通道本轮输出未收敛到完整结论，不计作通过证据。实际判断使用参考原图、源模型正侧面画面和骨骼测量。照片、模型、FBX 和密集动画数据仅保留本机。

局部检查已完成：整段采样中，上臂／小臂相对 rest 的最大骨长误差小于 0.0001%；推掌停顿区间使用相同姿态。正侧面模型画面显示腕臂过渡比 V4 平缓。右手原握姿未改；表中的整段最大扭转包含该施法入场之前的原握持姿态，不代表推掌终点。未运行 UE PIE 或战斗回归，实机姿态仍待用户复测。

`FPSGAMEEditor Win64 Development`、`FPSGAME Win64 Development` 常规构建均完成；日志 `build-editor.log`、`build-game.log`。编辑器无运行游戏、无未保存包时正常退出以更新基础 DLL，没有强制终止进程。
