# 符文战锤：替换锤头原装符文、PBR 与镇魂钟黄色电弧

覆盖清单：原装锤头保留；`heavy_forged`、`flanged_breaker`、`light_drum`、`pointed_hammer`、`star_oath_sealing_anvil`、`final_toll_soul_bell` 六款替换锤头均派生独立网格、原装符文烘焙遮罩及对应材质。握持、装配连接面、动画和战斗数值不变。

`surface_authoring.py` 从原装锤头的真实几何和原 UV 符文遮罩进行 selected-to-active 发光通道烘焙，把原图案转印到新锤头实体表面。通用锤头保留原有 UV 通道，增加专用符文 UV；两款传说锤头将图案写入自身表面图集，并烘焙 0.16 mm 符文凹槽法线。

两款传说使用其保留的构造源与实际装配边界，增加物理尺度的加工细纹、锻造微孔和金属光泽变化；主体重新烘焙 4K BaseColor / ORM / tangent Normal，细镶边独立烘焙 1K PBR 三图，原装符文遮罩为 2K。UE 法线使用 TC_NORMALMAP、线性采样及翻转绿色通道；ORM 为 R 遮蔽 / G 粗糙度 / B 金属度，颜色图保持 sRGB。原有细镶边实体、光学核心、钟室厚壁与轮廓保留。

`ProductionFinalTollLightning.cpp` 提供镇魂钟常驻黄色电弧，沿真实锤头坐标包围双侧钟室并延伸到锤颈。六条错峰短弧使用五边截面的三维细管，共 750 顶点、1440 三角形、一个动态网格组件；形态 30 Hz 更新，变换每帧跟随，35 m 外隐藏，无碰撞、动态灯、阴影或新增伤害。未苏醒时也显示，苏醒提高亮度；破坏符文不把这层指定黄色电弧改为红色。

材质沿现有装备异步加载，纹路接入当前 RuneAwake / RuneImpact / EnergyTint 参数。卸装、死亡、隐藏或换掉镇魂钟时隐藏电弧，结束时销毁本组件。第一人称和其他玩家的持有武器使用当前可见锤头组件。

作者入口：`author_legendary.py -- star_oath`、`author_legendary.py -- final_toll`、`author_common.py`。`import_assets.py` 保存独立 UE 资产；`publish.py` 按具体叶字段更新当前和作者模型配方。实际完成以 `import_receipt.json`、`build_receipt.json`、`published.json` 为准。

本次不生成验收渲染、不启动游戏、不运行测试；烘焙贴图属于生产资产，观感由用户体验。

2026-10-24 本地接入已完成：37 个 UE 资源保存，六款替换锤头的正式与作者配方已更新；原装锤头保留。后台导入以及 FPSGAMEEditor / FPSGAME 构建退出码均为 0。目录配方使用独立的写前原文比较与备份入口，未修改玩家身体配置。编辑器制作接口未连接，最终导入通过关闭编辑器后的 commandlet 完成，未自动重开 UE。
