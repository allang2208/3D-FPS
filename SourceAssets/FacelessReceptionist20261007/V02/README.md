# 无面接待员 V02

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

日期：2026-10-08（Asia/Shanghai）。

本版修正 V01 预览中暴露的大腿拉飞、袖下碎片、肩领开缝、裙子穿体和鞋面塌陷。作者文件、GLB、FBX、32 个 UE 资产已保存；已按用户请求制作 Blender 三视图。未启动 UE 图形编辑器、游戏或 PIE，没有游戏测试与动态动作验收。

## 当前文件
- Authoring/FacelessReceptionist_V02.blend：完整原身体、25 个独立服装/细节对象、原女僵尸骨架和 Idle/Walk/Attack 制作源动作。默认绑定姿态，NLA 静音。
- Delivery/FacelessReceptionist_V02.glb：穿衣角色，蒙皮与贴图内嵌，不包含动画片段。
- Delivery/FacelessReceptionist_Clothing_V02.glb：独立衣物与同一骨架，不包含原身体。
- Delivery/SK_FacelessReceptionist_V02.fbx：UE 合并穿衣网格，六个材质分区。
- Delivery/SK_FacelessReceptionist_Body_V02.fbx：完整身体。
- Preview20261008/FacelessReceptionist_V02_ThreeView.png：本版绑定姿态的正、侧、背三视图，Blender EEVEE 渲染。
- ue_delivery.json、Logs/import_v02.log：实际导入和保存回执；commandlet 退出码 0。
- ../Source/：用户原 GLB；../Authoring/Inputs.blend：制作恢复输入。V01 文件保留作问题追溯，当前使用 V02。

## 修正方法
原女僵尸供体在裙子下没有完整髋/大腿表面，无限制最近表面转权重把本模型大腿错误分配给手指。V02 对躯干和双腿按解剖骨链绑定，手部限定同侧供体；肩臂按空间骨段距离混合，避免袖内侧被躯干骨牵走。
修正手/脚目标变换的平移方向，并明确 hand 骨分类。读取源动作后恢复骨架容器的参考矩阵，防止动作对象位移留在导出参考姿态中。

原模型打底衣与裸臂表面分离；最终外套、衬衫在修正后的参考身体外生成连续网格和实体厚度。保留完整身体，没有通过删身或隐藏皮肤掩盖穿模。裙子依据原髋部截面增加覆盖余量，西装下摆覆盖裙腰；鞋面先封闭体积再重建，重新打开脚踝口。
深灰蓝西装、浅色衬衫、过膝裙、封口平底鞋、胸牌、袖口和翻领继续独立制作。身体 199526 三角面，衣物 181880 三角面，总计 381406；未再次减面原身体。衣物为骨骼蒙皮，没有 Chaos Cloth。

## UE 保存
继续使用 /Game/Monsters/FacelessReceptionist/BP_FacelessReceptionist 和原 F6 无面接待员入口。
穿衣与身体网格、六个材质、纹理以及关联资源已更新。女僵尸 Idle / Walk / Attack 动作副本、物理资产来源、行为和导航合同继续沿用原接入。
本轮未改 C++，无需触发新的原生构建。V01 的历史 Editor/Game 构建状态见 ../build_receipt.json；本轮不把旧 Game 构建失败声明为已解决。

## 重建顺序
从工程 Tools/FacelessReceptionist 按以下顺序后台执行：
1. author_character_v02.py：从原 Inputs 重新制作身体蒙皮、衣物基础和材质。
2. finish_tailoring_v02.py：围绕修正后的原生参考身体制作最终连续西装/衬衫，调整裙腰覆盖。
3. attach_source_actions_v02.py：保留三条女僵尸制作源动作并恢复骨架对象参考矩阵。
4. export_delivery_v02.py：导出 GLB、身体 FBX 与合并穿衣 FBX。
5. import_assets_v02.py：导入并保存原 UE 角色包；重新导入时设置 RECEPTIONIST_FORCE_REIMPORT=1。
6. render_reference_v02.py：仅在用户要求预览时生成三视图。

create_*、refine_*、close_* 与 finish_v02_fit.py 是本次脚本编辑过程记录；最终重建以以上生产脚本为准，不重新运行这些脚本生成器。

## 状态边界
三视图反映当前 Blender 绑定姿态，不代表 UE 动态蒙皮、裙摆运动、碰撞或游戏行为通过验收。仍由用户进行游戏测试。未公开分发原 Meshy 或商业女僵尸资源。
