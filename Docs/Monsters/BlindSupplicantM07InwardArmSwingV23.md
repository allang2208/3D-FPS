# M-07 V23：内向掌心与随步摆臂

日期：2026-10-03。工程：`D:/FPS3D/FPSGAME`。

用户体验 V22 后反馈：脚部、腿部动作没有太大问题，但手部僵硬、没有随步摆动，爪子掌心向外；要求掌心朝内并按步频摆动。已查看用户提供的本轮截图。该图用于理解手部姿态，单帧不能证明摆动幅度与完整周期；动态问题依据用户体验反馈处理。

## 改动

- 明确左右手的目标：掌心朝身体内侧。用当前胸廓坐标定义左手 -X／右手 +X，再以真实手腕、食指／小指指根平面计算掌面，不继续使用 V22 的共同“朝后”目标。
- 参考姿态中的肘几乎伸直，其轻微弯折方向在左右两边不同。使用朝前屈肘的解剖轴和有符号参考屈曲建立共同骨链，保留所有原绑定矩阵；不依靠单个手腕翻转 180° 修正掌面。
- 以原步态相位编排对侧摆臂：左脚前时右臂前、左臂后，下半周期相反。慢走上臂相对肩部制作角度约 -22.6° 至 +27.3°，追击约 -25.4° 至 +30.7°；肘屈曲在 18–36° 间随摆动变化。数值是作者参数，不是实机视觉测量。
- 锁骨／肩带先行，上臂响应延迟约 0.035–0.045 秒，肘部约 0.06–0.075 秒，腕部约 0.09–0.11 秒。前臂负责掌面转向，手腕保留小幅跟随，五指按同一步态周期轻微收放。
- 直接复制 V22 Action，只重写锁骨、上臂、前臂、手腕和手指曲线。腿脚、骨盆、五段脊柱、头颈、背膜的原曲线不重新生成。慢走／追击的 3.2／2.4 秒周期、42／86 cm/s 制作速度和当前游戏速度属性保留。

只修改两段移动动作。原显示几何、蒙皮、参考骨架、布料及其他动作保留；本轮不新增 C++、运行时 IK、Tick 或物理开销。

## 产物与接入

制作源、两个 FBX、两段 UE 动画及现有 AI／F6 蓝图引用均已实际保存；本轮回执记录 `saved=true`。速度字段没有写入，保留 42／86 cm/s。

- 作者脚本：`Tools/BlindSupplicantM07/author_inward_arm_swing_v23.py`
- UE 导入脚本：`Tools/BlindSupplicantM07/import_inward_arm_swing_v23.py`
- 制作目录：`SourceAssets/BlindSupplicantM07Meshy20261001/InwardArmSwingV23/Motion/`
- 可编辑源：上述目录 `M07_Original_InwardArmSwing_V23.blend`
- 导出：`A_M07_SlowWalk.fbx`、`A_M07_Chase.fbx`
- 清单：`inward_arm_swing_manifest_v23.json`；`authored_*_arm_record_v23.json` 是制作数据，不是测试报告。
- UE 目标：`/Game/Monsters/BlindSupplicantM07/AnimationsInwardArmV23/A_M07_SlowWalk`、`A_M07_Chase`
- 角色：现有 `/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07`，对应 F6「盲祷者 M-07」。仅替换两段移动及兼容 `walk_clip` 引用，不写入速度字段。
- 保存回执：`SourceAssets/BlindSupplicantM07Meshy20261001/InwardArmSwingV23/ue_inward_arm_delivery_v23.json`
- 修改前蓝图磁盘副本：上述制作根目录 `Before/BP_BlindSupplicantM07.uasset`；V22 动画资产仍保留。
- Blender 日志：`Saved/Logs/M07-InwardArmSwingV23-Author.log`
- UE 后台保存日志：`Saved/Logs/M07Import-20261003-111252.log`

本轮没有主动启动或重启 UE，没有启动游戏、PIE、截图、渲染或追加测试。初次通过现有桥等待编辑器连接时，编辑器已退出、未发现可连接节点，该次未执行导入；随后通过后台 commandlet 完成导入与保存。实际手部观感仍交由用户体验，不将脚腿的局部认可扩大成全角色动画验收。F6 重新生成「盲祷者 M-07」使用新移动引用。
