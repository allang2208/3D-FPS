# 唐刀第三人称旋风同步与刃面适配

后续用户明确要求“再把旋转的方向反过来”：运行配置已由 +720° 改为 -720°，保留本轮唐刀三段资产与身体朝向同步修正。以下记录为此前制作过程；当前方向以这条后续指令为准。本次仅修改配置，未运行游戏测试。

用户实机反馈：上轮仅改 `turnDegrees=-720` 后，唐刀第三人称旋风方向错乱；第一人称不在此次反馈范围。该全局反转方案已撤回，不能再称其为“恢复认可版本”。

## 两处不同的问题

- `URuneSwordComponent` 在 `TG_PostPhysics` 推进旋风控制器朝向，已晚于 `PlayerController::UpdateRotation` 对 Pawn 的 `FaceRotation`。引擎 `SetControlRotation` 不会同步转动 Pawn。因此相机读取本帧旋风角度时，第三人称身体仍可能保留上一帧朝向。现在最后一个旋风子步结束后调用 `FaceRotation`，再合成相机与可见姿态；命中暂停仍使用执行器同一时钟。
- 唐刀的既有 `bone_mount` 绕柄轴半转，实际单刃是原生 `WPN_root` 的 +X；通用 Kwang 正向挥斩按 -X 刃口制作。反转整个技能虽然能改变刀刃速度方向，却同时反转身体、镜头与攻击扫掠，无法作为这个安装差异的修复。

## 本次实现

`skills.json` 回到 +720°，与现行默认值一致。唐刀使用独立的 `Melee.FullBody.TangDao.Whirlwind.Start/Loop/End`，其余剑继续原三段。唐刀三段从恢复资产复制，骨轨道、接触标记、时长和根锁保留，不重跑被否定的肘极优化。

独立副本通过已有 `SwordGripRoll` 消费链适配单刃：起势前 85% 从 0 平滑到 -180°，挥斩保持 -180°，收势后 40% 回到 0。武器根围绕原生握柄长轴应用相反补偿，保留刀尖长轴轨迹、双手轴向握点与现有肩肘姿势。这是圆柄上的刃面调整；没有交换左右手或反向播放动画。唐刀三段切换也进入原先的连续接点分支，避免额外的 80 ms 混合拖后姿态。

作者入口：`SourceAssets/ThirdPersonTangDaoWhirlwind20261010/author_edge_roll.py`。
资产保存入口：`Tools/PlayerBody/save_tang_dao_whirlwind20261010.py`。
制作配置：同源目录 `edge-roll.json`；保存和接入结果分别记录于 `assets-saved.json`、`assets-published.json`。

普通竖劈、冲刺竖劈的现行左手接触版不在本次修改范围。

## 交付边界

原生构建已完成：`Saved/BuildEditor/build-20261010-195723.log`、`build-20261010-200112.log` 均为 `Succeeded`。首次保存已写出三段，但退出时收势资产的异步压缩仍在执行并触发断言。`WeaponAnimationAuthoring::FinalizeAuthoredAnimation` 现在在数据收尾前后等待该序列压缩结束；续存进程正常退出，退出码 0，`save-final-commandlet.log` 报告 `Success - 0 error(s)`。三个唐刀专用引用已接入 `player_body.json`。

未启动编辑器界面、PIE、截图、渲染或动作验收。后台写入和构建完成不代表唐刀所有握把的蒙皮接触或实机观感已经通过验证，由用户在游戏中测试。
