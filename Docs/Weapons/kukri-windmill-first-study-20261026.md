# 尼泊尔弯刀第三人称风车式旋风：第一版 V8

2026-10-26。用户否定上一版旋风并要求搜索《洛奇》单手剑风车参考后，授权“先做一版”。

## 参考边界

- [普攻接风车教程](https://www.youtube.com/watch?v=sY6HjMhnDUg)
- [Windmill Rank 5 演示](https://www.youtube.com/watch?v=c12vkqocnzI)

上述旧实机视频画质和视角不足以可靠辨认单手剑与左腕细节。这版是采用单手剑风车方向的原创三维适配，不是原游戏动作数据重定向，也不声称逐帧复刻。未提取或导入《洛奇》客户端资源。V7 的斧类身体起伏与上扬持刀轨迹不再作为本版运动曲线。

## 本版制作

- 起手：当前弯刀待机接屈膝、反向拧身蓄势；左臂先收至胸前，持刀臂先低位蓄力，再向身体外侧展开。
- 旋转：腰胸高度横扫，持刀臂保留软肘。胸腰只有有限幅度的相对转动，避免上一版反复举高持刀手、夸张侧倾的轮廓。
- 左臂：护胸、外侧平衡、回收形成连续曲线，肩肘配合；保持放松半握拳，手腕朝向按原生掌轴和前臂支撑制作。
- 下肢：降低重心，两脚按现有旋转时钟交替换支撑，低幅抬脚并允许脚尖转动；入场与收势顺序落脚。
- 收势：短暂顺势卸力、回收持刀臂与左手，回到现有待机；Start/Loop/End 使用同一边界姿态。
- 两套身体按各自实际网格绑定制作，保留弯刀握柄手型，并分配上下臂扭转辅助骨。

资产为 120 Hz。保持现有准备 0.5 秒、两圈旋转 1.066667 秒、收势 0.52 秒的业务时钟；收势资产 62 帧间隔，由现有阶段归一化映射播放。全局 -720° 继续由现有运行时负责，不在骨架上重复烘焙旋转。

## 文件与接入范围

六个原生 AnimSequence 已由后台 commandlet 保存，进程退出码为 0；六个第三人称旋风字段已通过配置事务接到 V8。旧 GUI 编辑器未由本任务关闭或重启，当前已运行的角色实例不作为新配置生效证据。

- 制作源：`SourceAssets/KukriWindmill20261026/author.py`
- 原生轨道：同目录 `jason-actions.json`、`kaitlin-actions.json`
- 保存入口：`save_jason.py`、`save_kaitlin.py`，共用 `save_assets.py`
- 配置入口：`publish.py`，使用 `Tools/PlayerBody/config_transaction.py`，仅写 Jason/Kaitlin 的六个 `Kukri.FullBody.Whirlwind.Start/Loop/End` 字段。
- 新资产目录：`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/<Jason|Kaitlin>/Animations/WhirlwindWindmillV8/`
- 名称：`A_Kukri_Whirlwind_<Start|Loop|End>_Windmill`
- 保存、接入的实际完成情况分别以本目录 `assets-saved.json` 和 `published.json` 为准。

第一人称、伤害、技能时长、剑气及其他第三人称攻击未修改。没有 C++ 改动，无需重新构建游戏模块。保留旧资产作为版本恢复输入，不覆盖原包。

## 交付边界

按用户规则后台制作与接入。现有编辑器的 Python 互斥桥未发现可连接节点，未执行写入；保存改用持同一互斥锁的后台 commandlet，只创建独立 V8 新包，已有包仅作读取输入。不主动启动或关闭 GUI 编辑器。不运行游戏、PIE、F6、渲染、压缩姿态检查或验收测试；自然度、服装覆盖和游戏最终表现由用户测试。这是一版待体验的动作候选，不标记为视觉合格。
