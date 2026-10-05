# 伏窥者空气炮预警 V11（2026-10-05）

用户要求在空气炮发射前添加明显特效，给玩家反应时间。

## 表现与时序

- 下伏起手即显示背环琥珀色双环、三束向内聚气和压力核心，配套吸气升调音效。复用实际内缘 16 个蒙皮顶点计算的中心、朝向和宽高，随当前骨架最终姿态贴合。
- 发射前摇从 0.92 s 延长到 1.50 s；第 1.20 s 锁定预判落点，最后 0.30 s 转成亮白色并播放短促提示，停止追踪目标转向。客户端使用同一服务器时钟截止点显示变色。
- 维持较大的可读轮廓：组件缩放由 1.08 缓慢收至 0.90，代替旧版 0.95 收至 0.38；提示在整个蓄力阶段持续可见，不高速闪烁。
- 发射时隐藏预警，播放原弹体／释放音效；被控制、打断、死亡或动作结束时清理提示和蓄力声。
- 使用 V09 的口部支撑／低伏姿态，保留前 0.34 s 下伏与发射后的反冲速度，仅延长中间蓄压。新动画 120 fps、293 帧、2.433333 s，第 181 帧（1 基）发射。尾帧因采样对齐多 0.003333 s。

## 范围与预算

复用原 `AirChargeRing` 组件，一个网格、一个材质槽、3360 个作者三角形；无新增 Tick、粒子 Actor、动态灯、贴图、碰撞或阴影。材质使用顶点色区分环／流束／核心，CPD 0／1／2 对应可见强度、蓄力进度和锁定状态；保留深度遮挡，不穿墙显示。材质 HLSL 见本目录 `AirWarning.hlsl`。

空气炮 48 物理伤害、命中眩晕 3 s、冷却 20 s、弹速及真实背环出口保持原值。飞扑 V09、死亡 V10、爬墙、速度、皮肤与骨架保持原引用。

## 可重建来源

- 作者：`Tools/LurkerM08/author_air_warning_v11.py`；输入 `MotionV09_20261005/M08_Attacks_MotionV09.blend`。
- 动画／特效源：`M08_AirWarning_Animated_V11.blend`、`Animations/A_M08_AttackAirCannon_AirWarningV11.fbx`、`SM_M08_AirWarning_V11.fbx`、`S_M08_AirWarning_Charge_V11.wav`。
- 原创本地几何、程序合成音效、已有 V09 动画重定时；无外部下载素材。
- 原生：`LurkerM08AirCannon.cpp`、`LurkerM08Monster.h`；修改前副本位于 `PreviousSource/`。
- 构建：`Tools/LurkerM08/Build-AirWarningV11.ps1`；安装：`Import-AirWarningV11.ps1` → `install_air_warning_v11.py`。
- 安装目标：`/Game/Monsters/LurkerM08/AirWarningV11/`；只更新原蓝图的预警网格／材质／蓄力音效和原动作集的 `AttackAirCannon` 引用。安装前副本位于 `Before/`。
- 全量恢复入口 `install_lurker.py` 在 V10 后接入 V11。

## 落盘状态

作者导出、常规 Editor 构建和无界面安装均已完成，构建及导入退出码均为 0。构建报告目标已是最新；安装实际保存新动画、预警材质／网格／音效、原动作集和原蓝图，共 6 个资产，回执状态 `air_warning_v11_saved_and_bound`。原蓝图已绑定独立预警资产，`AttackAirCannon` 已绑定新动画并将发射时点保存为 1.50 s；F6 入口仍为 `LurkerM08`。记录见 `build_state.txt`、`import_state.txt`、`installation.json`。

本轮未运行游戏、测试、截图或验收渲染；可见性与反应窗口由用户实机确认。

## 2026-10-05 归档说明

本目录中旧 Before、PreviousSource、before_references.json、Blender 上次保存和已替代定位文件（如存在）已移到 `trash/lurker-m08-retired-20261005/`。按工程 `Docs/Publication/LurkerM08_20261005/archive-manifest.json` 查询原路径及恢复目标；历史段落的旧位置不表示备份仍在本目录。仍供当前制作链读取的正式源继续保留。
