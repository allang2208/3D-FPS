from pathlib import Path
roots=[Path('C:/Users/allan/.codex/skills'),Path('D:/FPS3D/FPSGAME/skills')]
for root in roots:
 p=root/'ue5-weapon-workflow/references/weapon-finish.md';s=p.read_text(encoding='utf-8')
 start=s.index('- **材质来源优先取宿主枪体网格的同一个槽**')
 end=s.index('- **导入时不要合并材质槽**',start)
 s=s[:start]+'''- **原厂同类槽是材质来源，不是统一完成的证明**（2026-09-19 修订）：原件延长且 UV 对应时，可沿用该枪原厂弹匣槽；还需区分实际绑定、贴图采样与表面风格。只有原槽本身已经匹配该枪、原 UV 与材质通道确实对应时，才有依据直接沿用。若仍有色调、粗糙度、金属度或尺度差异，再按本页做枪型专用变体；不能仅凭同名或同路径宣称材质统一。
- **先处理绑定错误，再考虑重做涂层**：2026-09-19 用户反馈三枪扩容弹匣泛白、材质不统一，读取实际资源发现三者均为 `WorldGridMaterial`。旧脚本记录的是计划使用的宿主材质，不是资源实际槽值。UE Python 的结构数组元素按副本处理：`slot = slots[i]` → 修改 `slot.material_interface` → `slots[i] = slot` → `mesh.set_editor_property('static_materials', slots)` → 保存。或使用对应网格的 `set_material` API。只写 `slots[i].material_interface = material` 会丢失修改。导入回执记录实际绑定值，不用目标变量伪装读回；这属于制作/接入结果记录，不自动开启游戏测试。
- **绑定原槽与烘焙机匣图集不同**：整张机匣 BaseColor/ORM 通过盒式投影铺到小弹匣上，会带入零件边界、花斑和错误尺度。原厂同类件 UV 能复用时优先保留；需要新涂层时只使用合适的金属区域或程序化涂层，保留弹匣自身结构法线与非金属身份。此前 `ExtMagUniversal20260917` 的“定稿”描述撤销，不能把旧导入回执当成视觉通过。

'''+s[end:]
 p.write_text(s,encoding='utf-8')
 p=root/'ue5-weapon-workflow/references/extmag-lengthening.md';s=p.read_text(encoding='utf-8')
 old='- 原 UV 无法复用时，制作独立 UV 并从原件烘焙颜色、法线与粗糙度；不要套枪身图集或以机匣涂层替换弹匣材质。'
 new='- 原 UV 无法复用时，制作独立 UV 并从原件烘焙颜色、法线与粗糙度。需要与枪身统一时按 weapon-finish.md 处理相应涂层，不套整张机匣图集，不覆盖弹匣的结构法线、纹路与非金属身份。'
 s=s.replace(old,new)
 old='- 局部接缝或切线处理不能证明壳体无缺口。AKM 已获整体造型认可后发现下段开放边，采用局部补面而非整体重塑；保留上端功能开口。当前作者入口 SourceAssets/ExtMagContact20260919/seal_akm.py。数值闭合记录仅描述修补范围，不替代用户视觉验收。'
 new='- 用户后来明确 AKM 所指缺口在弹匣口。此前 seal_akm.py 只补下段开放边，不能据此称用户问题已修好。功能开口仍需要口缘厚度、内壁和托弹板；空腔开口不等于可以留下单面薄壳。先区分漏选零件、破面和原始源缺少内部结构，再局部补齐，不以双面材质或平盖遮住口部。本轮入口 SourceAssets/MagazineMouthFinish20260919/author_mouth.py 保留原外壳并补口缘、内壁和下沉托弹板；尚未实机验收。'
 s=s.replace(old,new)
 s+='\n- 普通与扩容弹匣若保留同一插接段和抓握截面，可复用同枪包握接触；不要把普通弹匣遗漏在修复之外。M4 本轮普通/空仓的标准弹匣改走 ExtMagContact 动作，弹鼓仍独立，QBZ/AKM 不套 M4 动作。\n- 材质必须落到实际资源槽。2026-09-19 三枪扩容件原来均为 WorldGridMaterial，原因是 UE Python 结构数组修改未写回；具体绑定方式见 weapon-finish.md。\n'
 p.write_text(s,encoding='utf-8')
