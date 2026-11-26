# 符文战锤：专属符文与镇魂钟外观修订

制作目录：`SourceAssets/RuneboundWarhammer20261022/RuneAndBellRefinement20261024`。

迅捷魔力符文使用上扬翼纹、中空菱印与速度短纹；破坏魔力符文使用碎裂晶核、断环和放射碎片。两者各有独立矢量源和纹样遮罩，通过已有锤柄圆柱投射放到通用符文相同的展示区（武器高度 42.5–76 cm），沿用对向双面排布。保留迅捷蓝色、破坏赤红和原生苏醒材质、粒子及全部数值。

`MeleeRuneVisual.cpp` 将两款专属符文纳入已有投射模式，破坏采用红色调色板；原生材质更新后继续更新叠层的预览时间。`ModularSwordVisual.cpp` 和 `ColdSteelIconResources.cpp` 同步预载锤柄材质与专属遮罩，复用现有异步资源准备。

两张符文图标按统一金属框母版用内置 imagegen 生成：厚倒角方框、四角铆钉、银色内圆环、深灰底板、灰白主印和框外透明边。提示词保存于 `imagegen_prompts.json`，PNG 与 UE Texture2D 一起部署。镇魂钟图标同步采用新版真实模型取景输入。

镇魂钟几何源位于 `SourceAssets/RuneboundWarhammer20261022/FinalTollHammerHeadV2`。保留原装安装切面与 91.6 cm 模块偏移，按既有参考改造三道拱窗：闭合 5 mm 深实体边框、内壁和嵌合青铜饰边；音柱细纹按圆柱表面贴合；顶盖饰纹随斜面变化；底座／顶梁文字限制在实际平面内；锤面边框与主印嵌入表面。导出 99,000 三角面、4K BaseColor／ORM／Normal，独立 V2 包保留 V1 来源。

制作、资产保存、正式引用、Editor/Game 构建分别以目录中的回执为准。未启动 UE 编辑器界面或游戏，未执行游戏、视觉或联机验收，交由用户测试。

最终 12 项新 UE 资产已在独立作者工程保存并安装回主工程，运行 PNG、模块配方和改造目录均已切换。新版 UI Texture2D 位于 `RuneIconsV3`；实际 UI 继续读取正式 PNG，旧 Texture2D 来源保留。

Editor 构建成功。Game 构建 exit 6：当前 `ColdSteelPlayerState.h` 中 `ServerSubmitProfileChunk` 声明为八参数，`.cpp` 调用／实现仍为六参数；保留该并行工作，未修改多人存档代码。本轮三个符文表现源码已编译，不能将此记录表述为 Game 构建成功。
