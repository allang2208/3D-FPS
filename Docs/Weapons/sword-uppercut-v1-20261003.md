# 第一人称持剑上挑 V1

当前设置包含 [V18 释放消耗 25 体力、基础冷却 8 秒](sword-uppercut-cost-cooldown-v18-20261004.md)、[V19 范围成长](sword-uppercut-range-v19-20261004.md) 和 [V20 前踏时序](sword-uppercut-lunge-contact-v20-20261004.md)。战斗与成长沿用 [V17](sword-uppercut-combat-v17-20261004.md)，V15 动画、V16 镜头与 150 cm 前踏距离继续使用。历史制作源的归档位置见 [整理发布](sword-uppercut-publication-20261004.md)。

当前运行参数为 [镜头与前踏 V16](sword-uppercut-feel-v16-20261004.md)：镜头拉扯为 V15 的 1.5 倍，前踏为 150 cm；动画仍使用 2.05 秒的 [对角镜头与握柄回位 V15](sword-uppercut-grip-recovery-v15-20261003.md)。主上挑仍为 0.075 秒，挥剑声与出手同步。沿用本页资产路径；本页以下为 V1 历史记录。

后续接入：用户反馈独立场景无法进入，现改为「上挑」主动技能，从技能页拖入快捷栏使用；参见 `Docs/Skills/sword-uppercut-20261003.md`。以下保留第一版动作和独立场景的制作记录。

2026-10-03。按用户指定制作：右下蓄势 → 向前上方斜挑 → 左上惯性带出 → 回到原待机。采用独立试播入口，未接入现有攻击连招或伤害判定。

## 试播入口

内容浏览器目录：`/Game/Weapons/SwordUppercut20261003/Preview`。

打开 `L_SwordUppercut_V1`，由用户运行该关卡，场景使用固定第一人称相机，自动循环动作。相机采用项目的 75° 垂直视场角，并固定 16:9。每轮上挑 1.45 秒，回位后保留 0.65 秒待机，总计 2.10 秒。

也可以由用户在游戏控制台输入：

```text
open /Game/Weapons/SwordUppercut20261003/Preview/L_SwordUppercut_V1
```

场景使用独立 `BP_SwordUppercutPreviewMode`、V7 裸手臂和项目现有原厂模块剑。它直接播放动画资产，不创建生产角色，不触发近战攻击逻辑。

## 动作资产

| 资产 | 用途 |
|---|---|
| `/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard` | 标准握距的完整动作，1.45 秒 |
| `/Game/Weapons/SwordUppercut20261003/LongGrip/A_Sword_UppercutV1_LongGrip` | 长握柄待机握距对应的动作候选，1.45 秒；未接入试播场景或共享动画 Profile |
| `/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard_PreviewLoop` | 独立场景循环，包含末尾 0.65 秒待机 |

| 时间 | 动作 |
|---|---|
| 0–0.42 秒 | 从原待机向右下蓄势 |
| 0.42–0.72 秒 | 剑向前上方斜挑，双臂随柄推进 |
| 0.72–0.85 秒 | 向左上惯性带出 |
| 0.85–1.45 秒 | 平滑回到原待机握姿 |

制作使用同一剑柄变换驱动双手抓握目标，保留手指原有握形、骨长和蒙皮。肩部参与位置补偿，双段手臂求解保持肘部弯曲方向连续；限制逐帧肘面变化，沿前臂辅助骨分配旋转，并以手腕弯折代价选择有限剑柄滚转。首尾使用同一待机姿态。上述为制作方式，未进行实播或画面验收，不代表已确认无扭曲或穿插。

## 可编辑交付与来源

`SourceAssets/SwordUppercut20261003/` 保存：

- `Standard/Sword_UppercutV1_Editable.blend` 和 `LongGrip/Sword_UppercutV1_Editable.blend`：原生 V7 手臂骨架上的可编辑关键帧。
- 对应目录内 `editable_keys.json`：120 Hz 原生 UE 骨骼局部变换。
- 对应目录内 `A_Sword_UppercutV1_*.fbx`：UE 导出的动画交换文件。
- `author_uppercut.py`：原创动作制作脚本；`install_uppercut.py`：动画与独立关卡落盘脚本。
- `inputs.json`：制作时读取的现有待机握姿和参考骨架；`authoring.json`、`install_receipt.json`：来源说明及保存回执。

上挑轨迹和关键帧为本次原创，没有下载、购买或使用 Fab 付费动画。复用的是项目已安装的 V7 手臂、剑模型和待机握姿。未把网络参考视频或第三方付费动作转换为素材。

制作与导入通过 Blender 后台及 UE Python commandlet 完成。交付状态以 `install_receipt.json` 中实际保存记录为准；没有主动打开/重启 UE 编辑器，没有运行游戏、自测、截图或渲染，由用户自行试播。
