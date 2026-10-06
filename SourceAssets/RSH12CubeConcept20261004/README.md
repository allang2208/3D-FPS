# RSH 方盒消音器概念与基础参数

用户要求：基础后坐力增加 25%，稳定性降低 25 点；消音器重做为贴合枪口的立方体式外观，先出图。

数值写入 `Content/ColdSteelData/gunsmith.json` 的 RSH base。后坐力 180 → 225；稳定性由现用 `FWeaponHandling::FromIndices` 在 shake=140 时的基础分数减去 25，再写成 base.stability_mult，沿用既有面板与实战同源入口。配件倍率继续叠乘。准确值见 `balance_receipt.json`。发布入口固定本次目标，重复运行不累计降幅；原始 RSH 建目录入口亦保留本次调参。

造型为外观概念：短方盒主体、宽平面、削角、短肩部贴合枪口，延续枪管护罩的方正轮廓。交付一张装枪侧前三分之四概念图 `RSH12_Cube_Concept_v1.png`，由内置 image_gen 生成；现用 RSH 图标作为宿主外形参考，原始图标倒置，在提示词中要求转为握柄向下。仅设计游戏美术外壳，不包含内部构造或制造图。完整成功提示词见 `prompt.txt`，来源和落盘路径见 `generation.json`。原计划多视图请求被图片服务拒绝，收窄到单幅游戏外观概念后已返回图片。

此次不制作或替换三维消音器，不改现用配件数值。未启动 UE、游戏或运行测试。上一轮双持动画的已授权后台导入和构建单独记录于 `RSH12DualReloadDrop20261004`。

## 加长概念 V2

用户已认可 V1 方盒造型，并要求在该基础上加长。`RSH12_Cube_Concept_v2_Long.png` 延长前方外壳及侧面浅槽，沿用削角与后端肩部外形。V1 保留作为已认可造型基准。V2 仍是外观概念图，未制作或替换 UE 模型。完整编辑提示词见 `prompt_v2_long.txt`，生成路径见 `generation_v2_long.json`。
