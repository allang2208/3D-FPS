# 龙息体积喷流制作与失败经验

本例为 FPSGAME 2026-10-14 Volume V8 R2。用户否定了多次 Sprite 喷流的纸片感与颗粒感；原火球／篝火获得认可不等于其龙息派生版获得认可。当前体积方案已保存，最终观感仍由用户试玩确认。

## 当前可重建链

- 入口 `Tools/Skills/build_dragon_breath.py` → `build_dragon_breath_volume.py` → `dragon_fluid_source.py`。
- 材质入口 `build_dragon_volume_color.py`，原创颜色 HLSL 为 `SourceAssets/DragonBreath20261013/VolumeV8R2_20261014/DragonFlameColor.hlsl`。
- 新机器没有 R1 材质时，R2 会调用 `repair_dragon_volume_visibility.py` 创建基线，因此 R1 修复脚本是有效依赖，不能当废案删除。
- 在独立 `SourceAssets/DragonBreath20261013/AuthorHost` 制作模块中后台编译／保存，启用 NiagaraFluids、NiagaraToolsets、Python 和 EditorScriptingUtilities。供体与插件按用户本机授权恢复，不把 Epic/Fab 包或图表导出当原创源码发布。
- 运行包仍为 `/Game/Skills/DragonBreath20261013/VolumeV8/NS_DragonVolume`，渲染材质为 `MI_DragonVolumeFlame_R2`。旧作者、一次性探针及被替代成品可归档，当前素材路径和共享火球母版保留。

## 避免再次出现反向、巨片和全白主体

- 先区分 Sprite 可见层与不可见流体源；只复制烟和火星不会得到火焰主体。图集行列、动态材质输入和 Renderer 必须与原包匹配，不能把不同图集解码互套。
- 体积路线需保留热源、三维温度／密度／速度场和 Volume Renderer 的完整输入。模板 Renderer 0 是调试切片，本例实际气体在 Renderer 1。
- 世界速度、局部网格索引和喷口坐标不能混用。移动网格开启运动补偿；伤害、源粒子行程和特效原点读取同一次施法的射程及喷口快照，客户端相对眼部的偏移由服务器限幅。
- 旧 Sprite 方案的粒子出生位置／方向必须自存，更新时读取当前喷口会拖动所有旧火片。插值生成可能缩短方向向量，作为速度方向使用前需归一化；修复方向不能靠随意翻转整个玩法前向。
- 本例体积纹理 G 为温度，R 为密度。模拟温度不是摄氏度。主体全白时依据已有温度数据调整颜色映射，颜色范围与消光／透明度范围分开，避免降高光同时把火柱变稀。
- R2 案例参数：颜色 0.35–160、增益 0.4、暗红至暖浅黄且无中性纯白端点；透明度温度仍为 0.35–5.3、增益 1.25、烟密度增益 0.18、单次曝光补偿。参数只适用于本例，不作为所有火焰默认值。

## 成本与证据

每施法者一个流体组件；本例热源 360/s、寿命上限 0.8 秒，本地最长轴分档 80/96/128/160/160，远端 80。停火立即结束伤害／发射，保留 0.65 秒尾焰；死亡与 EndPlay 清理。采样射线和距离场只是表现近似，伤害仍按实体遮挡独立判定；流体视觉边缘不等于硬裁剪的伤害半径。

曾出现 Niagara `IsValid` 为真但 CPU VM 缺生成状态的旧缓存问题。作者可明确请求完整编译，等待无 pending 后保存；单独 valid、保存成功或历史离线探针都不能替代当前画面验收。只有用户要求检查时才运行诊断 commandlet、GPU 回读或渲染。
