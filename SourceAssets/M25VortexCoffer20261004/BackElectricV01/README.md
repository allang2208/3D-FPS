# 涡电匣 M-25 背部电流 V01

用户已于 2026-10-04 确认此前模型、绑骨、待机和移动合格。本轮只增加背部电流表现，保留认可的网格、骨架、权重、动画、移速和既有追踪行为。

## 来源与制作

- 参考当前闪电魔法 /Game/Skills/Lightning/NS_LightningChain 的样条电弧；派生独立 /Game/Monsters/VortexCofferM25/VFX/NS_M25_BackElectric。
- 来源链：项目现有闪电魔法 → 本地已拥有的 Dr.Game Free Spline VFX。只在本地项目制作，不公开发布源 Niagara、纹理或材质。
- 使用现有九个 socket_electric_00—08 骨骼挂点，跟随同帧蒙皮姿态。
- 相邻电极之间错相放电；16—27 cm 的拱起让电弧跨在背部上方。
- 白蓝热芯约 0.85 cm、蓝色外晕约 3 cm；可用组件 Width 和 Brightness 调整。
- 主电弧 65 ms 平滑淡入、0.23—0.40 s 驻留、0.27—0.42 s 非线性冷却余辉，间隔错开。
- 路径每次放电只生成一次随机形状，持续跟随端点并进行小幅连续摆动，改换路径时旧弧已经熄灭。
- 第四条细分叉从活跃主电弧上生长；不延伸到嘴部、地面或玩家，不携带伤害、眩晕或声音。

## 运行预算

- 每只怪物复用四组样条/Niagara，不逐次生成电弧 Actor。
- 每条弧两个 CPU ribbon emitter，各 64 粒子，理论上限 512 粒子/怪物；去掉原 GPU Detail emitter。
- 近处最多三主弧、一短分叉；16 m 外不再新开分叉，22 m 外只新开一条主弧。
- 23.8—35 m 渐隐；35 m 外或模型不在画面时停止 Niagara，组件降为 5 Hz 判断恢复；15 m 外位置更新降为 30 Hz。
- 一盏 200 cm 半径的无阴影补光，峰值 55 lm，8—14 m 渐隐，不产生体积光或间接补光。
- 客户端本地纯表现，Dedicated Server 不加载/运行电流。角色销毁时取消加载并释放本轮组件。
- 上述为实现预算，未执行性能采样或帧率测试。

## 文件

- author_back_electric.py：派生 Niagara、设置绑定和预算、保存原怪物蓝图的新增组件。
- asset_receipt.json：实际保存与完成阶段，以 stage=assets_saved 为完整绑定完成。
- Source/FPSGAME/Monsters/M25BackElectricComponent.h/.cpp：运行时组件。
- VortexCofferM25 原生类新增 BackElectric 子组件。
- Before/：修改前的两份本怪物源码快照。
- 本轮构建/保存日志在本目录，不覆盖 UEV01 历史接入回执。

尚未自动运行游戏、截图、渲染或验收。当前背部电流由用户测试；此前“合格”仅对应已有模型与动作。

## 实际交付状态（2026-10-04）

专用 Niagara 与原 BP_VortexCofferM25 已通过后台 commandlet 编译、绑定并保存，asset_receipt.json 为 assets_saved，作者进程退出码 0。
Editor 常规构建 build_editor_03.log 与 Game 构建 build_game.log 均成功，未启动交互编辑器或游戏测试。

F6 → 怪物生成 → 涡电匣 M-25，新生成的怪物自动带背部电流。
可在蓝图继承组件 BackElectric 中调整 Electric Enabled、Brightness（24）、Width（1）与 Max Draw Distance（3500 cm）。

首次 Editor 构建遇到并行头文件的 UHT 错误，其原作者修订后继续；第二次构建发现本组件的 TObjectPtr 自动推导错误，已使用 Get() 修正。第三次构建成功。编辑器桥请求期间 UE 已退出，未执行资产写入，最终使用后台 commandlet 完成制作。历史失败日志保留，不能将本轮全部日志描述为零报错。

2026-10-05 整理：上文旧备份已移入仓库根 trash/m25-retired-20261005 的同阶段相对目录；逐文件映射见 Docs/AssetArchives/m25-retired-20261005.json。生产源与当前资源保留。
