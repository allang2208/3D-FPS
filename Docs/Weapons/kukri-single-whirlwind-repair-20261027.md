# 单持弯刀第三人称旋风 V18

承接双刀 V2 的肩肘与下蹲修正，更新 Jason、Kaitlin 的单持旋风 Start、Loop、End。作者入口为 `SourceAssets/KukriSingleWhirlwindRepair20261027/author.py`。

## 动作修改

- 下肢采用双刀 V2 的支撑方式：脚分处身体两侧，脚尖略向外，膝盖沿各自脚尖屈曲；取消旧单持脚部绕身体中线的反向旋转补偿。骨盆保持在支撑范围内，旋转中逐渐压低，收势分步站起。
- 持刀臂采用双刀 V2 的原生骨段解算：肩高外伸，与旋转同步展开；肘部弯曲面连续搬运，刀身保持向外水平，保留已有右手握柄与手指。刀面不再反向决定整条肩肘的轴向旋转。
- 空手独立制作，不使用双刀左手持握。左臂从待机移至体侧，肘部自然弯曲，随身体倾斜和旋转作小幅跟随；手腕沿前臂的原生局部关系放松，五指按不同幅度轻屈。
- 左肘弯曲面随手臂方向连续转移，避免线性肘目标穿过手臂轴线。收势沿相同连续曲线回到待机；辅助扭转骨和手指半关节由最终姿态派生。
- 三段动画来自同一条 120 Hz 时间线，首尾使用当前单持待机。旋转方向、技能时长与命中规则继续读取现有技能合同。

## 已完成的接入

无界面 commandlet 已成功保存六个原生身体动画，退出码为 0。资产分别位于：

`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/{Jason|Kaitlin}/Animations/WhirlwindSingleV18`

通过 `Tools/PlayerBody/config_transaction.py` 按字段更新两套身体的 `Kukri.FullBody.Whirlwind.Start`、`Kukri.FullBody.Whirlwind.Loop`、`Kukri.FullBody.Whirlwind.End`。保存回执为作者目录内 `assets-saved.json`，接入回执为 `published.json`。

本次为第三人称资产更新，没有新增 C++ 改动或执行额外构建。第一人称与双刀资产没有修改。旧 V17、双刀 V2 及其原生骨架工具仍是制作依赖，保留以供重制。

未启动编辑器界面、游戏或 PIE，未新增预览渲染或运行测试，游戏中的动作、衣服和武器最终效果由用户测试。已完成本地资产保存与配置接入；未重新打包游戏，未提交或推送 Git。
