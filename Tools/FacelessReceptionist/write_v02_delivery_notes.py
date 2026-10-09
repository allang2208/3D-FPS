from pathlib import Path
import json
base=Path(r'D:\FPS3D\FPSGAME\SourceAssets\FacelessReceptionist20261007')
root=base/'V02'
receipt=json.loads((root/'authoring_receipt.json').read_text(encoding='utf-8'))
cloth=sum(x['triangles'] for x in receipt['parts'])
readme=f"""# 无面接待员 V02
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
深灰蓝西装、浅色衬衫、过膝裙、封口平底鞋、胸牌、袖口和翻领继续独立制作。身体 {receipt['source_triangles']} 三角面，衣物 {cloth} 三角面，总计 {receipt['source_triangles']+cloth}；未再次减面原身体。衣物为骨骼蒙皮，没有 Chaos Cloth。

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
"""
(root/'README.md').write_text(readme,encoding='utf-8')
old=(base/'README.md').read_text(encoding='utf-8-sig')
prefix="""# 当前版本：V02（2026-10-08）
V01 在用户请求的三视图中暴露了错误蒙皮与衣物开缝，已由 [V02](V02/README.md) 替代。当前 Blender、GLB、FBX、三视图与 UE 保存回执在 V02 子目录；原版本保留作追溯。V02 已后台更新原角色资产，未游戏测试。

以下为 V01 历史记录，不代表当前造型通过验收。

"""
if not old.startswith('# 当前版本：V02'):(base/'README.md').write_text(prefix+old,encoding='utf-8')
doc=Path(r'D:\FPS3D\FPSGAME\Docs\Monsters\FacelessReceptionist20261008.md')
doc.write_text("""# 无面接待员 V02（2026-10-08）
当前制作包：[V02/README.md](../../SourceAssets/FacelessReceptionist20261007/V02/README.md)。

用户提供的减面 Meshy 无面女性身体保留。本次继续修正 V01：大腿曾错误转入女僵尸手指权重，袖内侧与躯干混绑；现按解剖区域处理，手部限定同侧供体。修正参考姿态转换及骨架容器残留位移。围绕修正后的原生绑定身体重做连续西装/衬衫，补齐裙子髋部覆盖和封口鞋。

完整身体、25 个独立衣物/细节对象、可编辑 Blender、穿衣/独立衣物 GLB、身体/合并穿衣 FBX、PBR 与 Blender 三视图已保存。身体 199526、衣物 181880、总计 381406 三角面；六个材质分区。服装仍为骨骼蒙皮，没有 Chaos Cloth。
原 /Game/Monsters/FacelessReceptionist 下的 32 个资产已后台更新保存，含原 BP_FacelessReceptionist、穿衣与完整身体网格、Skeleton/PhysicsAsset、材质纹理和三条女僵尸动作副本。F6 沿用无面接待员入口；未改 C++、地图、行为、命中时序或导航规格。

用户已要求三视图预览，本轮渲染为 Blender 绑定姿态。没有打开 UE 图形编辑器、启动游戏或 PIE，没有动态动作或游戏测试，由用户体验；未宣称 UE 视觉/玩法验收通过。实际保存记录见 V02/ue_delivery.json，commandlet 退出码 0。

V01 的源文件和导出保留作问题追溯。此前 Editor 构建成功、Game 构建因其他 Building 文件的 CubeMeshPath Unity 重定义失败，历史记录见制作包 build_receipt.json。本轮仅更新资产，没有重新构建，也不宣称此前独立 Game 构建问题已解决。
""",encoding='utf-8')
receipt['rendered']=True
receipt['preview']='Preview20261008/FacelessReceptionist_V02_ThreeView.png'
receipt['notes']=[n for n in receipt['notes'] if n!='No visual or gameplay acceptance performed.']
receipt['notes'].append('User-requested Blender three-view rendered. No UE runtime or animated-pose acceptance.')
receipt['notes']=list(dict.fromkeys(receipt['notes']))
(root/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
(root/'delivery_summary.json').write_text(json.dumps({'version':'V02','stage':'source_exports_and_ue_assets_saved','preview_rendered':True,'runtime_tested':False,'native_code_changed':False,'body_triangles':receipt['source_triangles'],'clothing_triangles':cloth,'ue_saved_assets':32,'commandlet_exit_code':0},indent=2),encoding='utf-8')
print('V02 documentation and delivery receipt saved')
