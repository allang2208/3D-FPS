# 镇魂钟二连重击：右上斜劈至左下，再接上挑

本轮按用户指定动作方向制作独立 V2 动作包，来源与脚本位于 `SourceAssets/RuneboundWarhammer20261022/FinalTollDiagonalV2`。

第一击借用双手剑重击的右上—前方—左下路径，适配战锤现有双手握柄和宽锤头。第二击从左下落点接续向前上挑，取消旧版低位与高位的整段冻结，改为有惯性的换向与收势。开始衔接原蓄力终点，结束衔接原待机。

第一人称沿用现有原生骨架和运行手模。两套第三人称身体各保存独立原生动画，通过 `player_body.json` 的 `Warhammer.FullBody.FinalTollHeavy` 精确角色键接入；不更改其他动作、衣物或身体配置。动作长度 1.25 秒、两次命中 0.10／0.42 秒、主要随动结束 0.54 秒均保持原合同，服务端伤害和体力逻辑不变。

第一人称加载路径由 `Production/FinalTollHeavyMotion.h` 指向 `/Game/Weapons/RuneboundWarhammer20261022/FinalTollDiagonalV2/A_Runebound_FinalToll_DiagonalHeavyV2`。资产保存、主工程安装与构建以制作目录中的回执为准。

未运行游戏、测试、截图或动作验收，最终观感由用户测试。

交付：3 份动画实际保存并接入，两个身体动作角色字段已更新；Editor 与 Game 最终构建均成功。Game 首次因并行家具／Kukri 源码不一致失败，待对应源码补齐后增量重建成功，未修改这些并行功能。
