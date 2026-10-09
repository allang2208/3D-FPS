# 无面男性安保 V11：连体领口与可击落安保帽

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

2026-10-09。针对颈部两侧与肩部衣物破洞反馈，修订 V10 作者源，并制作一顶独立安保帽及爆头脱落物理。按用户规则后台制作、编译、实际导入与保存；未运行游戏、渲染或追加验收。

## 领肩衣物

源数据中，上衣厚壳没有多余开放边；旧独立领座与上衣的宽领口采用不同的投射与权重，存在动作时露出间隙的可能。这是源数据定位和制作依据，不是游戏复现结论。

沿原生绑定空间保留 V10 上衣外表面、UV 和蒙皮，移除原生成内壁后，从实际领口的 99 个边界顶点共享延伸 12 圈面。新领口按完整身体颈部逐截面拟合，前低后高，上缘跟随颈部皮肤权重；过渡沿共享顶点连续化。最后统一生成 2.6 mm 内壁，内外层沿用相同权重。

移除独立领座与旧领片，局部调整领肩处 746 个外表面顶点的身体间距，肩章重新继承修改后主衣的表面和权重。完整身体不删颈部、不改骨架；V10 显示足踝与靴内遮挡、V09 手部、裤子和腰带保持。

独立衣物和穿衣组合分别交付，组合 221316 三角面。原 V06 待机／行走、V10 攻击恢复、速度、接地位置和命中窗口保持。

## 安保帽

深藏蓝低帽冠、黑色皮革短帽檐与帽带、银色盾形徽章和 SEC 字样。独立刚性网格 9736 三角面，沿用制服、皮革、深色饰边和金属四个材质族。帽子有真实内壁与佩戴开口。

- 作者版：`Authoring/SecurityServiceCap_Anatomical_V11.blend`。
- 引擎局部坐标版：`Authoring/SecurityServiceCap_EngineLocal_V11.blend`。
- 导入文件：`Delivery/SM_SecurityServiceCap_V11.fbx`，包含帽冠、帽檐两组 UCX 凸碰撞体。
- 佩戴骨骼：现有 `head`；局部偏移由当前 UE 参考骨骼与作者坐标换算，记录在 `authoring_receipt.json`。

`USecurityHatComponent` 仅添加到原安保蓝图。佩戴时跟随头骨、无碰撞，监听角色已有 PointDamage 事件；正伤害且命中 head 或其子骨时只触发一次，致死爆头也能触发。身体命中不触发，原伤害数值和死亡处理不变。

`ASecurityDroppedHat` 使用同一网格及佩戴当时的世界变换，质量 0.32 kg，继承角色速度，按射击方向叠加上抛冲量及旋转。使用 Chaos 重力、凸碰撞、CCD 和阻尼，与世界静态／动态物体碰撞，不阻挡角色；35 秒后回收，独立于原怪物尸体寿命。脱落状态和掉落物移动支持网络复制，两类均不添加 Tick。

## 已保存接入

- `/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_V11`
- `/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_Clothing_V11`
- `/Game/Monsters/FacelessSecurity/Accessories/SM_SecurityServiceCap_V11`
- 原 `/Game/Monsters/FacelessSecurity/BP_FacelessSecurity`，F6 仍是“无面安保”。

完整身体继续使用原 V09 资产；本目录完整身体导出仅作恢复配套。没有修改女接待员或通用怪物动作。

Editor 与 Game 两个原生目标均构建成功，记录在 `build_receipt.json`。无界面 commandlet 已实际导入保存上述资产，`ue_delivery.json` 为 `saved`，最终退出码 0。第一次导入遇到 Python 不暴露重叠事件 setter，已移除多余调用，沿用原生构造函数关闭重叠事件，再完成蓝图保存。FBX 导入沿用原骨架，日志记录导入器重新生成 bind pose 成功。

未启动 UE 图形编辑器、PIE 或游戏，未渲染。领肩动作观感、帽子佩戴位置和爆头落地效果由用户测试，未宣称运行验收通过。

制作入口：`Tools/FacelessSecurity/author_neck_hat_v11.py`、`import_neck_hat_v11.py`、`build_security_hat_v11.ps1`。运行代码：`Source/FPSGAME/Monsters/SecurityHatComponent.*`、`SecurityDroppedHat.*`。
