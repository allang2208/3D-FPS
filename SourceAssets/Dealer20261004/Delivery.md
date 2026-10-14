# 庄家扑克牌作者源

当前发牌规则为两张随机底牌加五张公共牌，仍在第五次有效命中七张取最佳五张；算法见 `Docs/Combat/enchant-dealer-holdem-20261004.md`。当前显示改为 `SelectionV5`：首次抽牌显示上排两张底牌，下排五个公共牌槽位，七张各自漂浮；结算保留原位，用牌轮廓火焰标识实际入选五张。源码、原创 HLSL 和独立保存入口在 `SelectionV5`；完整恢复入口也已接入。说明 `Docs/Combat/enchant-dealer-seven-card-selection-20261004.md`，本次必要构建另记 `Saved/DealerSelectionV5/delivery.json`；未运行游戏、预览或测试。此前概率调整的构建回执为 `Saved/DealerHoldem20261004/delivery.json`。

当前显示版本为 `InfernalV2`：独立水平悬浮牌、原创新字体 Infernal Dealer、九个英文结果、无背景边框及 ×4/×5/×7 分档火焰。完整作者入口和导入入口已切换到 V2；详情见 `Docs/Combat/enchant-dealer-infernal-v2-20261004.md`。首版构建回执为历史结果，本轮另记 `Saved/DealerInfernalV2/delivery.json`。

高倍音效追加 `AudioV3`：Freesound scorpion67890 的 CC0「Demonic Laugh」，公开 HQ MP3 预览加工为短 PCM 笑声；来源、许可与制作参数保存在该目录。×4／×5／×7 的 Burst 首次显示帧各播一次，分档音量与音高，最多一个笑声音部。独立制作／导入入口及完整恢复入口均已接入，SoundWave 已通过后台 commandlet 实际保存，Game／Editor 必要构建均成功。回执单独记在 `Saved/DealerLaugh20261004/delivery.json` 和 `AudioV3/install-receipt.json`；说明见 `Docs/Combat/enchant-dealer-demon-laugh-20261004.md`。本轮未试听或实机测试。

原创卡牌几何、四花色 52 张牌面、牌背与九个结算牌型图集。编辑源 `DealerDeck.blend` 包含 52 张共享几何的牌面编辑实例及打包纹理；运行时统一复用 `SM_DealerCard` 与一份图集。

制作：`run_author.ps1`；实际 UE 导入/保存：`run_install.ps1`；必要原生构建：`run_build.ps1`。脚本不启动游戏，不执行测试或预览渲染。

资产目录 `/Game/Weapons/Dealer20261004`。图集和模型均由脚本原创制作；原始牌面使用系统字体栅格化进纹理，不分发系统字体文件。V2 结算字体 Infernal Dealer 为原创多边形字形，保存独立 TTF、SVG 和火焰遮罩源。具体玩法、倍率与临时牌组生命周期见 `Docs/Combat/enchant-dealer-revolver-20261004.md`。

初版保存两网格、四材质、三纹理。V2 当前交付：原创英文结算字体、图集、更新后的 Blender 作者源及源码已保存；另外已导入/保存一份火焰字体遮罩、两个 V2 材质和结果网格的新材质绑定。V2 制作回执 `complete=true`，本轮 Game/Editor 构建均成功。未启动游戏、测试或验收渲染。
