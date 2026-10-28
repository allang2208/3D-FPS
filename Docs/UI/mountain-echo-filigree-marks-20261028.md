# 山鸣弓弦：三枚镂空纹章

> 历史方案；当前实现以 [mountain-echo-alpine-20261028.md](mountain-echo-alpine-20261028.md) 与发布清单为准。退役实物文件的恢复位置见 `Docs/Publication/HighlandBow20261028/archive-manifest.json`。

用户要求将准星下三个标记改为更精细华丽的线条纹路，命中后逐个点亮。本轮直接改造现有 `ColdSteelBowResonance.cpp` 的 Slate 自绘层。

- 外观：双层弓叶弧线、羽状卷边、山峰箭芯、冠饰与底部编结。沿用 HUDGold / HUDGoldLight / HUDGoldDim；暗态为低亮金铜轮廓，亮态为金线与局部光晕，没有实心底板。
- 布局：三枚横排、中心间距 34 px，总线条宽度 98 px，中心在拉弓条下 20 px，纹路高度 22 px。复用现有 PixelScale 与小视口限位，底缘仍位于准星下 95 px；增益闪光不缩放图案。
- 数据：只读 `UBowMountainEchoComponent::ChargesFor`、`GainAge`、`ReadyAge`，沿用满弓有效命中后由服务端增加层数的原规则。敌人／训练靶判定、层数时限、弦影箭消费规则均由现有玩法维护。
- 动画：左、中、右依层数点亮；新获得的一枚用 0.30 秒描亮纹路和短促箭芯闪光。相邻两枚都亮才点亮连接刻线。满三枚后，待描亮结束播放一次扩散光环，并保留轻微呼吸亮度。
- 生命周期与输入：继续在现有准星 NativePaint 路径绘制；装备、死亡、翻越、菜单隐藏沿用现有入口。没有新增控件、委托、计时器、输入焦点或存档字段，不占用操作。
- 性能：14 条单位纹路及累计长度首次使用时缓存；每帧复用一个小绘制缓冲，只变换固定顶点并截取新命中动画。细节线不铺多层光晕，不加载贴图或解析物品数据。

本轮为矢量绘制源码，无新增需要导入的 uasset。构建记录位于 `SourceAssets/WoodSteelLongbow20261026/MountainEchoMarksV20`。默认不进行运行测试、截图或视觉验收，由用户测试。

交付状态（2026-10-28）：编辑器退出后，已完成 FPSGAMEEditor 与 FPSGAME Win64 Development 常规构建，均为 Succeeded。交付以基础 DLL 与游戏目标为准，不以此前发起的 Live Coding 请求作为生效凭据；未主动打开 UE、运行游戏或进行视觉测试。
