# 符文战锤原装件图标 V2

2026-10-23 按改造栏新版标准，使用内置 image_gen 分别生成四张原装件图标。实际模块造型沿用 ModulesV1；本轮只更换二维图。

- 双侧锤头：成对外锤头作为一个模块，保留中央安装空隙及原有刻纹。
- 中央锤座：保留原装哥特拱纹、顶盖、凹槽与连接端。
- 握持包覆：保持竖向细长比例，区分皮革与金属箍。
- 柄尾配重：保留分层八棱轮廓与收束尾端。

边框使用已批准的厚倒角金属方框、四角铆钉、银色内环和不透明深灰底板；仅极窄框外边缘透明。整体采用中性灰阶。采用现成同款“无附加符文”图作边框参考，移除其中的减号主印；该空槽图自身不修改。

每张母图同时发布到原装选项键与对应分类入口，并同步 ModulesV1/Icons 中的正式图。当前读取入口为 Source/FPSGAME/UI/M4GunsmithLayout.cpp 的 LoadCategoryIcons / BuildOption，使用 FImageUtils::ImportFileAsTexture2D 直接读取 PNG，无需额外制作未使用的 Texture2D 镜像，也无需原生编译。

manifest.json 保存最终提示词、内置生成器、实际部件参考、安装方向及发布映射；Masters 保存正式母图；Before 保存替换前输入与运行图；Receipts 保存实际文件发布回执。publish.py 只复制文件并记录图片元数据，不修改图片像素。

重发正式图使用：py -3.11 SourceAssets/RuneboundWarhammer20261022/FactoryFramedIconsV2/publish.py

未修改整锤背包图、无附加符文、固定锤颈/长柄图和通用配件图。未启动 UE、游戏或进行运行测试，由用户测试改造台显示。
