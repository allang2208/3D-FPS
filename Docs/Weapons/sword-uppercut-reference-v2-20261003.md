# 上挑 V2：参考左侧人物的完整上挑

用户随后反馈「还是不合格」，本版已被 [箭步上挑 V3](sword-uppercut-arrow-step-v3-20261003.md) 替代。以下为历史制作记录，不表示用户认可。

2026-10-03。视频：[德国梅耶流长剑的16个实用招式](https://www.bilibili.com/video/BV1yx41187zP/)，重点 33–36 秒。用户最初写右侧，查看画面后由用户明确选择「按左侧的完整上挑轨迹调整」。

通过正常网页播放器定位并观看该段；另看 30–33 秒衔接，区分右侧的下劈／前伸和左侧的上挑。浏览器画面记录在 `SourceAssets/SwordUppercut20261003/ReferenceRevision/frame-*.png`，只作本地制作参考，不作为可再分发素材。没有下载或引入视频动画数据、付费动作或第三方关键帧。

## 动作改动

参考可见特征是左侧人物双手从身前低位向上提起，最后剑柄到头侧，双肘继续弯曲支撑，剑尖指向对手。此次将原来「手较低、剑向左上大幅甩出」改为完整的双手高位收势。原视频是侧视且含慢动作；进深、第一人称摆位及播放时长为三维改编，不宣称逐帧重建。

| 动作时间 | 制作内容 |
|---|---|
| 0–0.32 秒 | 从原待机收至右下低位，紧凑蓄势 |
| 0.32–0.80 秒 | 双手和剑向前上方斜挑，肩肘随动，剑柄继续提到头侧 |
| 0.80–0.96 秒 | 高位收势，剑身回到朝前的指向，肘部保留弯曲 |
| 0.96–1.60 秒 | 从前方卸力，平滑返回原待机 |

手与剑柄的相对矩阵沿用各自待机，手指和握距不变。完整肩—上臂—肘—前臂链采用原生骨长解算；前臂扭转辅助骨承担新增旋转，肘面按连续分支推进。剑柄位置和剑身方向采用分别设计、连续切线的曲线，双手共同跟随同一持握变换。上述为制作方法，不等同于实机无扭曲验收。

## 实际保存与运行引用

沿用已接好的「上挑」主动技能和原资产路径，路径里的 V1 是固定接入名称，内容已更新为 V2：

- `/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard`：标准柄，1.60 秒。
- `/Game/Weapons/SwordUppercut20261003/LongGrip/A_Sword_UppercutV1_LongGrip`：长握柄，1.60 秒。
- `/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard_PreviewLoop`：相同 V2 动作，加 0.65 秒末尾待机，共 2.25 秒。

`RuneSwordComponent` 已按片段实际长度播放，因此此次资产更新无需修改或重编 C++。技能绑定、占用和结束回位沿用现有接入，不新增数值、消耗、伤害或修炼。

制作源：`SourceAssets/SwordUppercut20261003/ReferenceRevision/author_uppercut_v2.py`；两套可编辑 `Sword_UppercutV2_Editable.blend`、`editable_keys.json` 与 `A_Sword_UppercutV2_*.fbx` 位于其 Standard／LongGrip 子目录。V1 作者文件仍在上级目录，改动前已保存的包保留在 `ReferenceRevision/PreviousAssets/`。

Blender 后台制作完成。落盘时已有 UE 编辑器运行，因此通过项目 MCP 桥批次互斥写入、导出并保存三支动画；没有另开或重启编辑器。`ReferenceRevision/install_receipt.json` 与 `install_bridge_result.txt` 记录实际保存结果。

未运行游戏、测试、验收截图或渲染，由用户通过现有上挑技能自行试玩。
