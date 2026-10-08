# 缚群衣物 V18：肩背承重、独立袖口与渐变布料

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

后续状态：用户于 2026-10-08 否定衣物效果并要求删除重建。正式外观已改用 [V19 重新制作](bound-congregate-garment-rebuild-v19-20261008.md)；本页保留制作历史，V18 不是合格服装模板。

用户要求：保留衣物材质，按巫婆服装制作经验重新处理布料。2026-10-08 用户回复“继续”，授权实施此前方案。默认后台制作、构建、导入和保存；不启动编辑器、游戏、渲染或测试。

## 制作范围

- 从 `GarmentContinuityV14` 制作独立 `GarmentDrapeV18` 候选，保留肉体、触手、参考骨架和现有动作。
- 左侧长衣片由躯干承重；右侧衣片移至后肩，绕开触手根部及相邻肢体。衣片保留连续表面，边缘采用宽缓的破损轮廓，避免针状碎条。
- 长衣片只从躯干骨链取得支撑权重，再沿连通布面平滑；不混入独立肢体或攻击触手权重。两个袖口分别只跟随 `leg_L2_lower`、`leg_R4_lower`，裁片避开关节。
- 显示表面和低密度模拟代理分开。代理共 1,915 个作者顶点；显示表面细分后添加单次 3 mm 厚度。圆筒接缝保持几何焊接，UV 接缝独立。
- 保留已有材质资产引用、织纹 UV 比例、G 通道磨边与 B 通道脏污；A 通道记录固定边至自由下摆的驱动力遮罩。
- 背带局部接触调整限制在 3.5 cm 内，防止跨开口的带面被最近点吸到开口边缘。标牌沿背带安放。

## 布料配置

`BoundCongregateAuthoring.cpp` 中仅对名称含 `GarmentDrapeV18` 的网格启用新配置，旧版本配置保持可用。

- 固定边的位移为零，过渡区逐渐释放；左衣片最大活动范围 7 cm，右衣片 5.5 cm，袖口 2.4 cm。
- 增加逐点 Anim Drive 遮罩：主衣片刚度范围 0.025–0.42，袖口 0.08–0.48。自由布边与缝合区域分开驱动。
- 使用更厚重的布料密度、弯曲刚度及阻尼；降低继承速度，使快速攻击对衣物的牵扯减弱。
- 继续复用巫婆 `UWitchRebuiltClothingAsset` 的稳定位置、法线、切线绑定。该稳定绑定在 V14 已存在，本次没有把它当作缺失功能重做。
- 碰撞体按衣片附近的躯干、根部与所属肢体选取，每件最多 16 个胶囊。保留骨骼局部单位换算，继续禁用造成过往卡顿的 CCD；没有新增逐帧顶点遍历。
- 保留现有远距离布料暂停/恢复及动作系统。甩鞭、120 度判定、2 s CD、F 三次解缠、V17 撕咬与连续拍击不在本次修改范围。

## 文件与接入

- 作者脚本：`Tools/BoundCongregate/author_garment_drape_v18.py`
- 源模型与 FBX：`SourceAssets/BoundCongregateMeshy20261006/GarmentDrapeV18/`
- 原生布料构建：`Source/FPSGAME/Monsters/BoundCongregateAuthoring.cpp`
- 导入保存：`Tools/BoundCongregate/import_garment_drape_v18.py`
- 后台执行入口：`Tools/BoundCongregate/finish_garment_drape_v18.ps1`
- 现有编辑器接入：通过 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript` 执行 `prepare_garment_drape_v18_editor.py`，释放互斥后在外部执行 `author_soft_corpse.py --garment-v18`，最后通过同一桥执行 `finish_garment_drape_v18_editor.py`。
- 目标网格：`/Game/Monsters/BoundCongregate/GarmentDrapeV18/SK_BoundCongregate_GarmentDrapeV18`
- 目标死亡模型：同目录 `Corpse/SK_BoundCongregate_CorpseV18`，重新生成对应的软体嵌入数据。

导入使用独立骨架，兼容原 V14 骨架及已有动作。先保存新网格、布料和死亡模型，最后仅修改 `BP_BoundCongregate.VisualMesh`。原材料及 V14 资源保留。需要回退时恢复 VisualMesh 引用，不整包覆盖其他并行玩法修改。

## 当前交付状态

源模型、FBX 和代码已制作，Editor 与 Game 的 Development 构建均已完成。

用户退出 PIE 后，已通过现有编辑器互斥桥完成分阶段接入：新骨架、网格、四件布料绑定、死亡网格、软体数据及 `BP_BoundCongregate.VisualMesh` 均已保存。最终 `delivery.json` 记录 `saved: true`，正式外观已切换至 V18。

外部软体制作输出 672 个节点、2,202 个四面体。相关制作记录分别为 `import-editor-prepare-03.log`、`soft-corpse-author.log` 和 `import-editor-finish-01.log`。未自行开启、关闭编辑器或启动 PIE，未联系其他任务。

未进行游戏运行、画面渲染或布料效果测试。制作和构建成功不代表动态效果已获用户认可，仍由用户体验后反馈。
