# 庄家 V2：独立悬浮扑克牌与恶魔火焰字效

同日追加的高倍同步恶魔笑声已完成音源制作、SoundWave 落盘及必要构建，见 [高倍结算笑声](enchant-dealer-demon-laugh-20261004.md)；仍未试听或实机测试。

本次为用户指定的显示优化：镜头前悬浮、水平排列且不重叠、逐牌独立上下浮动；结算英文、去掉背景边框、设计火焰字体，以及高倍独特特效。仅调整表现与显示生命周期，保留抽牌、暴击兼容规则、九档倍率和第五次有效命中结算。

## 牌的位置与运动

`UDealerEnchantmentComponent` 仍从实际本地玩家透视矩阵和相机姿态构建 80 cm 的相机空间，随镜头移动而留在左侧空中。预留五个固定横向槽位，物理牌宽 6.3 cm、间距 7.55 cm；新牌直接进入下一空槽，已有牌不向中心平移、不穿过另一张牌。行宽按视口投影约束在 NDC 0.52，高度同样限制，兼顾 ADS、横向宽屏和窄窗口。

每张牌由牌 ID 与槽位确定独立装饰相位，不调用战斗随机数。上下振幅 0.28–0.38 cm、角频率 1.45–1.99 rad/s，另有很小的纵深呼吸、偏航和侧倾；共同转身摆动缩减为有限微倾，不破坏水平间距。入场仍保留轻微翻动和抬升，现有牌不重新播放入场。

## 原创 Infernal Dealer 字体

作者源 `SourceAssets/Dealer20261004/InfernalV2/author_titles.py` 定义全部 A–Z、数字与小数点的原创多边形字形：尖角衬线、矛尖顶饰、削角字腹、较粗竖画与可读的字间距。不是现成字体加描边。保留 `InfernalDealer-SpearSerif.ttf`、`InfernalDealer-Glyphs.svg` 和图集源码，可继续扩充字母或重制风格。原始牌面字体沿用初版，本次新字体只用于结算字效。

| 结算文字 | 倍率 | 独特表现 |
|---|---:|---|
| HIGH CARD | 1 | 焦黑金属、熔金边缘、轻微字顶火舌 |
| ONE PAIR | 1.5 | 同源字效 |
| TWO PAIR | 1.75 | 同源字效 |
| THREE OF A KIND | 2 | 同源字效 |
| STRAIGHT | 2.5 | 同源字效 |
| FLUSH | 3 | 同源字效 |
| FULL HOUSE | 4 | 升温字效、额外余烬与短火苗 |
| FOUR OF A KIND | 5 | 四束独立火焰冠向上窜升 |
| STRAIGHT FLUSH | 7 | 恶魔双角轮廓、连贯火焰冠与余烬 |

倍率字样同样使用该字形，以 `X1`、`X1.5` 等显示在英文牌型下方。结果片只覆盖字形、字顶火焰与软辉光，RGBA 空白不显示矩形，不存在背景面板或边框。

制作图集 4096 × 1024，3 × 3 共九个标题；R=实心字形、G=熔金倒角、B=火焰锚点、A=柔和字周辉光。材质独立读取稳定字形和动态扭曲火焰，避免文字随火焰噪声变形而失去可读性。仅一次反曝光补偿；透明材质在景深之后绘制，禁用场景深度遮挡，只有拥有者可见。

## 生命周期与预算

- 牌的五张结算淡出与结果标题寿命分开：牌组在 1.65–2.2 秒淡出；普通结果标题 2.4 秒、高倍 3 秒，末 0.6 秒淡出。下一发子弹命中新一手时继续保留上次结果文字和火焰，下一次五张结算会替换上次结果。
- 高倍指 ×4 及以上，三个等级分别对应葫芦、四条和同花顺。高倍效果仅在结算时激活，不改变抽牌或伤害；火焰位于牌组与文字后方，不叠加新后处理，不闪白全屏，不新增局部灯。
- 沿用五个牌组件和一个标题组件，增加一个池化高倍特效片；高倍最多一层，18 个解析余烬和四条火苗写在同一有界材质中，没有持续创建粒子 Actor 或灯。新资源与现有牌一起异步预取，不在命中或逐帧路径读盘。
- 字效是针对近景相机附着的动态材质，不是 Mantaflow 模拟；没有为几个结果标题启动体积烟模拟。

## 实际制作入口

- `InfernalV2/author_titles.py`：字体、SVG、生产 Mask 图集及给 Blender 使用的彩色 RGBA 字效图集。
- `SourceAssets/Dealer20261004/run_author.ps1`：完整牌组作者入口已切到 V2 英文字效，同时更新可编辑 `DealerDeck.blend` 的打包结果纹理；后续重制不会恢复中文背景短签。
- `InfernalV2/install_ue.py` / `run_install.ps1`：只导入新遮罩、创建两个 V2 材质并保存结果网格的材质绑定；已有编辑器使用批次互斥，未打开编辑器时用后台 commandlet。保留原结果网格包到 `InfernalV2/BackupV1`。
- 基础 `install_ue.py` 在完整导入后继续调用 V2 制作入口，不把当前表现改回旧材质。
- 运行资产 `/Game/Weapons/Dealer20261004/InfernalV2/Textures/T_DealerInfernalMasks`、`Materials/M_DealerInfernalTitle`、`Materials/M_DealerInfernalBurst`；标题与高倍特效复用原 `SM_DealerResult` 几何。
- 必要构建 `run_build.ps1 -OutputSubdirectory DealerInfernalV2`；制作、资产保存与构建回执分别保留，初版的构建回执不会被当成本轮结果。

字体制作依赖 Pillow 和 fontTools；本轮将 fontTools 4.66.1 安装在 `Saved/DealerInfernalV2/PythonPackages`，未修改全局 Python。原创字体和图集可随本工程使用，不含第三方字体轮廓。

## 交付状态

原创字体、九个英文标题图集、更新后的 Blender 作者源和运行源码已落盘。实际已导入并保存 `T_DealerInfernalMasks`、`M_DealerInfernalTitle`、`M_DealerInfernalBurst`，以及原 `SM_DealerResult` 的新材质绑定；V2 `install-receipt.json` 为 `complete=true`。本轮 Game 和 Editor 必要构建均成功，回执 `Saved/DealerInfernalV2/delivery.json` 两目标均为 `succeeded`。

本轮没有主动启动或重启 UE，也没有启动游戏、测试、截图或验收渲染；实际观感交由用户测试。制作中存在的共享原生任务按进程队列等待完成，未向其他任务发送协调消息，未关闭已有编辑器。
