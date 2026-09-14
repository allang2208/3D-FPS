# Gunplay V7：增强烟火与镜内动态火光

后续精修见 [V8：浓白烟与柔化火光](gunplay-vfx-v8-20260914.md)。本页保留 V7 的参数与制作记录。

按用户“烟雾和火光几乎不可见、镜内火光僵硬”的反馈调整。V7 接替 V6 的两套烟火系统；曳光及抛壳继续沿用当前实现。

## 表现调整

- 火光恢复更多原始 HDR 亮度：普通约为源色的 0.85 倍、LPVO 为 1.05 倍，每发再随机乘 0.88–1.14；此前固定为 0.30 倍。ADS 尺寸乘数由 0.78 改为 0.94。
- 原装枪口尺寸由 0.19 改为普通 0.27、LPVO 0.25。LPVO 仍按瞄具类型识别，覆盖 1–6x 及退镜渐隐。
- 亮芯寿命 35–52 ms，前焰 45–75 ms，侧焰 38–65 ms。各层独立出生寿命、短起势及非线性透明度消退，消除同步硬切的图案感。
- 前焰和侧焰的纹理两轴按粒子年龄独立伸展、收拢。出生时保存尺寸，更新时从出生尺寸计算，避免逐帧乘法累积。
- 每发改变真实侧焰角度、长度随机度和侧焰出现概率；LPVO 侧焰概率范围 0.45–0.75，减少整齐、持续重复的焰瓣。实际枪口位置和射击方向不变。
- 烟雾默认透明度由 0.36 提高到 0.60，每发烟取普通 0.72、LPVO 0.648；尺寸乘数从 0.19 提高到 0.28。烟色略提亮，材质提高不透明度增益和环境补光，近距淡出从 55 cm 降为 8 cm。
- 每发烟寿命 0.65–0.95 s，源尺寸 44–64；停火余烟 0.90–1.25 s、源尺寸 38–56，热烟尺寸乘数 0.24。停火后热量超过 0.24 开始出余烟，仍按 0.16 s 周期发射。
- 消音器继续保留较小火光和独立烟量。LPVO 开镜隐藏新旧弹壳，退镜完成后恢复。保留转轮手枪不随每次射击抛壳的并行改动。

## 作者入口和本机依赖

- `Tools/AssetPipeline/build_gunplay_presentation_v7.py`：从本机 V6 复制并制作 V7，不改写 Epic 原始包或 V6。
- `Source/FPSGAME/Weapons/FPSWeaponFXComponent.h/.cpp`：运行参数与资产引用。
- `/Game/Weapons/GunplayFX/NS_FPS_MuzzleEpicV7`、`NS_FPS_BarrelSmokeEpicV7`。
- `/Game/Weapons/GunplayFX/MI_MuzzleSmokeV7`、`MI_BarrelWispyV7`。
- 恢复顺序：合法 Epic NiagaraExamples → V5 → V6 → V7。源素材与派生 uasset 沿用原许可，仅作为本机依赖；没有引入第三方 GitHub 代码。

本轮仅完成资产制作、源码接入和必要构建，不启动游戏、截图或运行测试。实际可见度、连续开火和 1–6x 镜内观感由用户测试；本文参数描述不代表视觉验收通过。

资产制作记录：`Saved/Logs/GunplayV7-Assets-20260914-c.log`；两套 Niagara 编译完成，四项资产保存完成，清单为 `Saved/GunplayVFX20260914/created-assets-v7.json`。Commandlet 整体退出码为 1，仍包含项目已有的 GameFeatureData 资产管理配置错误；本次 Python 制作脚本执行成功，没有修改该无关配置。

普通 Editor 原生构建完成：`Saved/BuildEditor/build-20260914-001144.log`，`Result: Succeeded`。等待并行构建结束后，由工程 `Tools/Build/Build-Editor.ps1` 生成普通名称的游戏及插件模块；没有启动游戏测试。
