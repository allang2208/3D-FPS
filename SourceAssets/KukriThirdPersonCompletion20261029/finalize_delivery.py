"""Collect the scoped delivery evidence after the final background review."""
import json
from datetime import datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8-sig"))


checks = {name: read(name) for name in (
    "source-checks.json", "saved-checks.json", "network-checks.json",
    "uppercut-final-pose-checks.json")}
build = read("build.json")
assets = read("assets-saved.json")
manifest = read("asset-manifest.json")
assert assets["complete"] and len(manifest["assets"]) == 14
assert {b["target"] for b in build["builds"]} == {"FPSGAMEEditor", "FPSGAME"}
assert all(b["exit_code"] == 0 for b in build["builds"])
assert all(d["failures"] == 0 for d in checks.values())
counts = {name: len(data["checks"]) for name, data in checks.items()}
poses = checks["uppercut-final-pose-checks.json"]
saved = checks["saved-checks.json"]
wrist = max(c["value"] for c in poses["checks"] if c["case"].endswith("wrist bend degrees"))
arm_depth = max(c["value"] for c in poses["checks"] if c["case"].endswith("arms outside torso cm"))
rotation_error = max(c["source_rotation_error_degrees"] for c in saved["checks"])
position_error = max(c["source_position_error_cm"] for c in saved["checks"])
receipt = {
    "completed_at": datetime.now().astimezone().isoformat(),
    "asset_count": 14,
    "bodies": list(assets["bodies"]),
    "builds": build["builds"],
    "checks": {k: {"count": counts[k], "failures": 0} for k in checks},
    "final_uppercut_pose": {"max_wrist_bend_deg": wrist, "max_sampled_forearm_torso_depth_cm": arm_depth},
    "saved_compression_error": {"rotation_deg": rotation_error, "position_cm": position_error},
    "editor_gui_started": False,
    "pie_or_udp_tested": False,
    "first_person_animation_changed": False,
    "asset_manifest": str(OUT / "asset-manifest.json"),
    "publication_receipt": str(OUT / "published.json"),
}
(OUT / "delivery.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

report = ROOT / "Docs/Weapons/kukri-third-person-completion-20261029.md"
report.parent.mkdir(parents=True, exist_ok=True)
rows = "\n".join(f"| {name} | {count} | 0 |" for name, count in counts.items())
report.write_text(f"""# 弯刀第三人称遗漏动作补齐 — 2026-10-29

本批次已经完成制作、后台导入保存、配置接入及 Editor/Game 正式构建。Jason、Kaitlin 各新增或更新 7 条原生骨架动画，共 14 条。当前主连击一、二段和第一人称动画未重做。

## 已交付动作

| 动作 | 接入键 | 处理内容 |
| --- | --- | --- |
| 单持装备 | `Kukri.FullBody.Equip` | 抛刀、张手、旋转、接刀，与实际武器模型的相对位置同步 |
| 双持装备 | `Kukri.FullBody.Dual.Equip` | 双手错峰抛接，独立左右刀身轨迹 |
| 主手手枪、副手刀上挑 | `Pistol.KukriUppercut` | 左手上挑、换握与回收；右手保留当前手枪的实际握持；支持蹲姿与视线变化 |
| 双持快速近战 | `Kukri.FullBody.Dual.Pommel` | 主手向前击打，副手持刀护持和配重，恢复双刀待机 |
| 双持跑步过渡 | `Kukri.FullBody.Dual.Run` | 按跑步权重过渡上半身，主刀翻为反握，下半身保留当前移动步态 |
| 双持第一段回收 | `Kukri.FullBody.Dual.Recover1` | 从已完成回刀的攻击尾帧平顺收势，不追加一次挥击 |
| 双持第二段回收 | `Kukri.FullBody.Dual.Recover2` | 同上，保留既有第二段主体动作 |

资产目录为 `/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/{{Jason|Kaitlin}}/Animations/Completion20261029/`。
`player_body.json` 通过 `Tools/PlayerBody/config_transaction.py` 仅发布本批次的 14 个配置叶节点。
完整资产路径、磁盘大小及 SHA-256 见 [asset-manifest.json](../../SourceAssets/KukriThirdPersonCompletion20261029/asset-manifest.json)，配置发布回执见 [published.json](../../SourceAssets/KukriThirdPersonCompletion20261029/published.json)。

## 制作中定位并修复的问题

- 手枪加副手刀上挑没有进入第三人称专用动作；已连接已有动作状态、进度、节奏和停顿信息。
- 混搭上挑的武器家族仍为 Pistol，旧蹲姿分支只识别 Kukri，导致蹲姿中途回到站姿。已将该原生上挑纳入蹲姿适配。
- 蹲姿低头的上挑进入和回收阶段存在前臂穿胸。现在为两只手保留向前的活动空间，并在短暂的进入混合后重新求解手臂。
- 单纯调整避让会增加左手折腕，现同时放松掌向并重新求解肩、肘、前臂，保持刀柄在手中的安装关系。
- 最终装备握拳层会盖掉抛接张手和上挑换握手指。对应动作现在保留动画里的原生手指，右手手枪仍使用当前枪械的握持。
- 双持快速近战的旧来源存在手部突跳，已重做肩部带动的击打弧线和回收。

第三人称刀身在最终身体姿态输出后，基于稳定的原始安装变换应用抛接、换握和跑步翻刀。使用既有角色装备/动作状态，不新增客户端伤害判定或额外 RPC。

## 已完成检查

| 证据文件 | 检查数量 | 失败 |
| --- | ---: | ---: |
{rows}

- 保存后重新读取全部 14 个动画，核对角色骨架、配置路由和压缩姿态；最大局部旋转误差 {rotation_error:.3f}°，最大局部平移误差 {position_error:.5f} cm。
- 上挑最终姿态检查实际加载 UE 动画实例和武器，覆盖 2 个身体、5 种手枪、4 种姿态/视线条件。所采样的前臂对躯干包络最大侵入 {arm_depth:.3f} cm，最大手腕折角 {wrist:.2f}°；同时检查枪柄位置、方向、刀尖上升幅度和最终手指层。
- 83 项联机相关检查是动作路由、攻击回执及服务器规则检查，**不是 UDP 多客户端运行测试**。
- `FPSGAMEEditor Win64 Development`、`FPSGAME Win64 Development` 均构建成功。检查使用无界面 commandlet，临时禁用当前缺失模块的可选插件 `FPSDeformationResidency`，未修改项目插件配置。
- 未启动 UE 编辑器界面或 PIE，未进行实机联机、网络延迟、不同服装动态穿插验收。自然度与实际游戏手感仍需游戏内观察，不能由构建和数值检查代替。

## 可查看预览

这些 GIF 来自**已保存资产的压缩姿态**，不是游戏录像；上挑预览未放入手枪模型，跑步预览展示上半身过渡，未展示游戏中的下半身移动步态。

- [单持装备](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Equip.gif)
- [双持装备](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Dual.Equip.gif)
- [副手刀上挑](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Pistol.KukriUppercut.gif)
- [双持快速近战](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Dual.Pommel.gif)
- [双持跑步过渡](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Dual.Run.gif)
- [双持第一段回收](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Dual.Recover1.gif)
- [双持第二段回收](../../SourceAssets/KukriThirdPersonCompletion20261029/Preview/jason-Kukri.FullBody.Dual.Recover2.gif)

制作脚本、保存脚本、姿态输入、检查结果及构建日志位于 `SourceAssets/KukriThirdPersonCompletion20261029/`。汇总见 [delivery.json](../../SourceAssets/KukriThirdPersonCompletion20261029/delivery.json)。
""", encoding="utf-8")
print(json.dumps({"report": str(report), "checks": counts, "max_wrist_deg": wrist, "max_arm_depth_cm": arm_depth}, ensure_ascii=False))
