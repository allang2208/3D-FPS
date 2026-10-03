# 矿泉水（2026-10-03）

- ID `mineral_water`，普通消耗品，1×2，可旋转；每瓶独占一件，不堆叠。
- 每次成功喝水恢复30点水分，最高不超过当前最大水分；水分已满时拒绝使用。
- 每瓶2次。第一次留半瓶，第二次移除物品。`remainingUses`保存在实例Data中，与恢复效果一起走既有档案事务；仓库、夹层、丢弃和拾取沿用相同实例。
- 复用现有药水的原生左手/备用V7裸臂与动作占用。水瓶独立22cm、抓握17.2cm；入口结算仍在1.46秒，结束2.45秒。饮用前开盖，结束拧盖、下放收回；入口前中断不消耗，入口后不退款、不扔掉仍可用的半瓶。
- 满瓶→半瓶→空瓶：持有液体通过动态材质FillHeightCm压平上层顶点，下降液面而不收窄水体。地面满瓶/半瓶为同源闭合网格，背包、夹层、仓库、快捷栏使用同源满瓶/半瓶图标。卡片及快捷栏标示2/2、1/2；详情显示恢复水分、剩余次数和满/半瓶状态。
- 候选来源：Fab [Plastic Water Bottle / Model Wala](https://www.fab.com/listings/543bb27e-896f-4603-aa12-5fb565b4ea60)。本地取得包`D:/FPS3D/VaultCache/FabLibrary/Plastic_Water_Bottle-543bb27e/fbx`；包内metadata保存作者免费商业/个人使用说明，原始资源与其再分发许可不作为本次公开发布交付。
- 保留原瓶筋纹与盖齿几何，只取一套瓶体/瓶盖，重新居中并统一cm尺寸；制作绿盖、清泉标签、透明PET及独立水体。UE透明材质采用当前Thin Translucent实时近似。
- 作者文件、脚本及导入回执：`SourceAssets/MineralWater20261003`。正式资产目录`/Game/Items/Consumables/MineralWater20261003`；图标`Content/ColdSteelData/Icons/mineral_water_full.png`、`mineral_water_half.png`。
- 获取方式：F6开发面板→消耗品→矿泉水。没有自动发放物品、修改个人存档或增加商店/掉落分布。
- 按用户规则仅制作、导入保存和必要构建；未进行游戏测试、动作验收或场景截图。

## 本轮构建记录

常规 `FPSGAMEEditor Win64 Development` 与 `FPSGAME Win64 Development` 已构建成功并写入二进制。日志分别为 `Saved/BuildSurvival20261003/FPSGAMEEditor-20261003-102415.log` 与 `Saved/BuildSurvival20261003/FPSGAME-20261003-102613.log`。资产导入保存状态以同目录制作源内的 `import_receipt.json` 为准；构建不代表游戏或视觉测试。

后台导入已完成并保存5个网格（瓶体、瓶盖、水体、满瓶、半瓶）、4个材质与标签贴图；commandlet日志为 `Saved/Logs/MineralWaterImport-20261003-102914.log`。满/半瓶PNG已落在物品图标目录。未开启交互编辑器、游戏或测试。
