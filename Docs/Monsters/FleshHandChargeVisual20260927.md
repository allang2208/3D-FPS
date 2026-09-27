# 异变巨手冲锋表现优化

用户授权按「绷紧、爆发、碰撞、刹停」方案制作。仅改大手冲锋的动画、提示、装饰和声音；蓄力 1.2 秒、冲锋速度与距离、伤害、眩晕、提前量、冷却和拍击合同保持原值。掌心伸拳和拍击召唤仍为停用状态，小手不加入主动冲锋。

## 动作与特效

- 三段冲锋动作重新烘焙：蓄力腕部后压至约 14°，闭拳后加入幅度不超过 0.65° 的短促用力颤动，末段前送至冲锋姿态；收势强化回压卸力。继续使用既有指腹拟合、外扣拇指、原骨架与蒙皮。根骨接地补偿改为正确的骨骼局部坐标，作者文件与旧 FBX 已保留。
- 蓄力脚下橙环从 280 cm 宽收拢到 180 cm，脉动随进度加快，短箭头跟随角色朝向。该箭头只提示当前朝向，不预画尚未确定的完整冲锋路线；正式提前量仍在冲出前计算一次。
- 皮肤叠加层利用本怪 BaseColor 的暗色细节遮罩进行轻微黄绿提亮，不改变基础感染材质。中断/收势恢复原叠加层，不覆盖其他系统后来设置的材质。
- 起冲：脚下后喷尘土和拳前短空气弧。冲锋中：两侧短气流、每 0.12 秒最多一次轻扬尘；尾迹长度与真实速度相联，最大 180 cm。
- 碰撞：复用实际胶囊首次阻挡事件，在接触点按接触法线展开 0.23 秒空气弧；非 Pawn 场景接触附加小碎屑。受伤玩家的冲击弧仅在实际伤害为正时出现，格挡/弹反和原玩家受伤反馈仍由现有战斗流程处理。
- 落空收势扬尘；无有效冲锋路线时直接收势，不生成起冲或刹停尘爆。死亡、击飞、控制打断和销毁释放当前占用。已产生的短寿命尘土/冲击弧自然消散。
- 新增原创合成的 1.2 秒低频蓄力声、0.36 秒破风声，单声道 24 kHz PCM；沿用原命中音效。声音有空间衰减，不给每个粒子附加音源。

## 运行预算

`UFleshHandChargeFX` 为本怪家族共享的世界装饰池，最多 8 组（包含淡出占位）。三个 ISM 渲染组件分别承载最多 64 张尘土片、24 张气流/冲击弧片和 32 个极小碎屑；最多 8 个可复用音频组件。复用项目已有 Mantaflow 烟密度图集和 `UFluidPresentationSubsystem::AllocateDetail`／风接口，没有新增实时流体求解、粒子灯、刚体或每粒子碰撞。

18 m 外减少每次尘土数量并省略碎屑，35 m 外不申请完整装饰，已活动对象移至 38 m 外释放。池满跳过装饰，已有橙环/方向提示和权威伤害不受装饰池影响。每个世界没有活动槽时停止装饰 Tick；没有为每只手增加常驻组件 Tick。资源由主怪蓝图持有，命中和 Tick 中不做同步磁盘加载。尸体/旧召唤/其他怪物不在此修改范围。

这是实现上限，未进行 FPS、GPU 帧时或多怪同屏采样。沿现有单机/服务器权威怪物状态入口接入，不额外声明多人客户端特效复制已实现。

## 作者与落盘入口

- `SourceAssets/FleshHand20260926/author_charge.py`：重新制作与导出三段动画。
- `author_charge_audio.py`：生成两段原创声音，来源回执在 `ChargeVisual/audio_source.json`。
- `install_charge.py`：导入三段动画并保存原有主怪参数。
- `install_charge_visual.py`：制作五份专用材质、导入两段声音、将材质/网格/声音绑定到大手蓝图。
- `install_charge_visual_all.py`：本轮动画与特效接入入口。完整 `install_ue.py` 同步增加特效步骤，重建不会丢失效果或恢复退役攻击。
- 原生入口：`FleshHandMonster.*` 与 `FleshHandChargeFX.*`；特效资产目标 `/Game/Monsters/FleshHand/ChargeVisual20260927/`。

常规构建已成功：`Saved/BuildEditor/build-20260927-133252.log`。三段动画已在 `ChargeVisual/import.log` 的动画阶段导入并保存；五份材质、两段声音和大手蓝图最终由后台 commandlet 保存成功（`ChargeVisual/import_v2.log`，退出码 0）。`Charge/ue_installation.json` 与 `ChargeVisual/installation.json` 均为 `assets_saved_and_bound`。原生逻辑及绑定已落盘；材质使用 NullRHI 作者入口，没有声明真实画面或 SM6 运行观感通过验收。没有主动启动 GUI、游戏、PIE、截图或渲染，也未执行测试，由用户自行试玩确认观感。

## 冲锋马赛克修复（2026-09-27）

用户反馈的马赛克已定位到 `M_HandChargeAir`：气流遮罩把 HLSL 保留字 `line` 用作变量名，PCD3D_SM6 编译报错并回退到默认棋盘格材质。改为 `trailMask`，将完整遮罩源独立保存为 `SourceAssets/FleshHand20260926/ChargeAir.hlsl`。`install_charge_visual.py` 对新建和已有材质均读取该源，通过节点标识及输入集合只更新气流遮罩节点。

`repair_charge_air_material.py` 已在后台 D3D12／SM6 commandlet 中完成目标材质重编译和保存，未使用 NullRHI；原资产保留在 `ChargeVisual/MosaicRepair/M_HandChargeAir.before.uasset`。本次编译日志 `ChargeVisual/MosaicRepair/compile.log` 记录 0 个错误及保存成功，回执为同目录 `repair.json`。现有气流与冲击弧共用此修复；不增加粒子、贴图或运行组件。未启动 GUI、试玩、截图或视觉测试，实际观感由用户确认。
