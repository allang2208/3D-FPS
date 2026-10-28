# 狂战士激活表现

仅在狂战士20s状态期间启用，读取既有服务器状态，不增加命中、伤害或体力事务。

- 镜头边缘：红色流动火舌、柔和红光，进入时短暂增强；左右各约15%、底部约18%、顶部约10.5%，中央完全透明。位于游戏HUD与改造面板下层，不能接收输入。
- 手部 V2：每手从28枚增加到128枚（96枚亮芯浮光、32枚柔和光晕），双手最多256枚。发射范围由手掌延伸到前臂，持续沿世界上方向升起，叠加缓慢横向飘动；不再以高速环绕的细碎长条为主体。亮芯寿命1.4–2.6s、柔光寿命2.2–3.3s，分散相位循环并柔和淡入淡出。双刀都安装狂战士符文时两手显示，只安装一枚则显示对应手；兼容手枪加副手弯刀。
- 武器 V2：激活时对对应刀身、握柄、柄尾、挂件等当前装配组件加临时红色发光层，整体转红，轮廓更亮，进入瞬间短暂增强。通过现有网格 OverlayMaterial 呈现，不替换原材质槽；状态结束、换武器、死亡或组件销毁时恢复先前覆盖材质，并保留其他系统后来接管的覆盖层。
- 本地第一人称可见，0.2s淡入、结束后约0.4s淡出；切换装备或死亡立即关闭。第三人称、非本人视角或隐藏HUD时隐藏。
- 两个有界实例化粒子组件加一层屏幕材质、一个共享武器红光MID，无新Actor、动态灯、碰撞、阴影或持续地面残留。三份程序化材质无新增纹理；装备时异步加载，休眠时停止更新。武器装配每0.15s随现有骨骼解析刷新，仅查对应刀根的模块子组件。

`author_materials.py` 创建并保存本目录HLSL对应的UE材质；保存结果见 `material-receipt.json`。原生接入为 `KukriBerserkerVFXComponent`，由 `KukriBerserkerComponent::Present` 驱动。

V2 参考源为 `ProductionRuneboundPassive.cpp` 的觉醒命中浮光、`RuneboundWarhammer20261022/PassiveV1/RuneboundMote.hlsl` 的柔边亮芯，以及 `DestructionRedImpactV2/DestructionMote.hlsl` 的红色能量。只提取其浮动与发光表现，不改战锤资产或命中机制。粒子中心跟随当前手臂，避免挥刀后整团脱离手部；上浮方向不随镜头俯仰翻转。

材质后台编译保存入口：`../WolfHeadComposite/install-queued.ps1 -PythonName '../ActiveFX/author_materials.py' -CompileShaders`；原生构建入口：`build-editor.ps1`。构建结果见 `build-editor.log`，与实机观感分别记录。

按用户规则未进行游戏测试、截图、性能采样或视觉验收。
