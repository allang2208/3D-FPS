# 百目炉渣大右手修订 V4

使用 RuntimeV3 的十万面游戏表面和已烘焙皮肤，分段驱动现有躯干，加入六根右臂辅助变形骨并调整局部权重，重新制作奔跑、回程、横扫与抬手重击。作者骨架为 43 根骨骼，其中 39 根变形骨，最多四个顶点影响。

模型为 `Delivery/SK_HundredEyedSlag_HeroHandV4.fbx`，十六条动画位于 `Delivery/Animations`。源文件为 `HundredEyedSlag_HeroHandV4.blend`。动画时长、速度和伤害窗口保持原合同。

后台安装原位保存 V1、PolishV2 网格、骨架、物理及十九个动画资产，F6 百目炉渣直接使用原引用。安装状态以 `installation_complete.json` 为准。重建入口 `Rebuild.ps1` 支持 `All`、`Authoring` 和 `Install`；保留 V3 作为几何、UV 和法线制作来源，不再导入原始高模。

未运行游戏测试或新增渲染。详细制作说明见 `D:/FPS3D/FPSGAME/Docs/Monsters/hundred-eyed-slag-hero-hand-v4-20260930.md`。
