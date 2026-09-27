# 幽蓝灵体剑命中：蓝色魔法爆炸 V3

用户反馈 V2 光点过小、命中不明显，要求蓝色爆炸。只调整命中视觉，伤害、暴击、魔法易伤、碰撞半径、射程和冷却保持原规则。

## 当前制作

- 三层主体：亮蓝爆心（约 0.28 秒）、扩张冲击环（约 0.62 秒）、蓝色起伏光晕（约 0.65 秒）。冲击环接近消散前可达约 1.6 米直径。
- 40 个飞散粒子：30 个半径 2.5～5 cm 光点、10 条长 18～32 cm 的短光丝；初速 280～460 cm/s，解析阻尼向外衰减，整体 1 秒消散。
- 复用飞剑已有无阴影点光源，命中时短暂照亮 2.2 米范围内的表面，0.24 秒内衰减至零；没有新增灯光组件。
- 同一个 ISM 组件承载三个爆炸主体和 40 个粒子，共 43 个实例、258 个源三角面。全部复用已保存的 SM_SpectralImpactParticle 六三角面网格，不重新导入模型。
- M_SpectralImpact 的解析材质按 PerInstanceCustomData 第 0 项区分光点、爆心、光环和光晕，经 VertexInterpolator 传入像素阶段，兼容非 Nanite 实例。材质无贴图依赖，UV 边缘透明，避免可见方形边界。
- 继续保留已加深蓝色、提高不透明度的剑体和原尾迹。

作者入口为上级 import_spectral_blade.py；本目录 import_blue_explosion.py 仅保存 M_SpectralImpact，不改剑体材质和网格。修改前的命中源码、材质作者脚本和材质包在 Before/。

## 构建和落盘

常规构建已包含本版 RuneOrbBladeProjectile.cpp 并成功链接 UnrealEditor-FPSGAME.dll。构建来自制作期间已运行的全模块构建，记录另存 native-build-shared.log（原 Saved/BuildEditor/build-20260927-202521.log），没有再排一轮重复构建。

材质已保存，import_receipt.json 记录 saved=true、compiler_errors=[]，后台 import_commandlet.log 记录 Success - 0 error(s)。开始时编辑器仍在运行，桥接准备期间编辑器关闭，桥请求没有找到可连接编辑器；之后按后台规则使用 commandlet 保存材质。没有启动 GUI、游戏、截图或执行测试，视觉效果由用户测试。
