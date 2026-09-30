# M55 当前仅保留弹链参数

201 弹链沿用 PKM 进弹链制作参数：速度衰减 13/s、轨迹回拉 1050/s²、重力倍率 1、偏移通道 4 mm、子步 240 Hz。参数通过现有 `FPKMSoftChain` 的配置入口使用，PKM 原有松链配置保持原值。开火细摆来自 Feed13 的短扰动；这些代码已在公共仓库 `Source/FPSGAME/Weapons/` 中。

M55 提把方案已按用户要求由 [H56](../HandleRemoval56/README.md) 撤除。原作者源、安装器和历史说明归档到本机 `trash/lmg201-publication-20261001/SourceAssets/LMG20120260927/Motion55/`。不能重新运行旧 `install_handle.py` 恢复已否决的提把。

当前弹链模型与接触为 [B53](../BeltFit53/README.md)，固定入口修整为 [F57](../FeedMouth57/README.md)。当前代码、已保存资产与用户验收分别记录；本轮只整理发布资料，未运行游戏。
