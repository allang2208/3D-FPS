# 715 配件独立聚合物材质

用户要求手电、枪灯相关改造件使用自身聚合物材质，并补充全息瞄准镜。本次覆盖 flashlight、laser、holographic 三类；主体保留已认可的 Chrome，全景红点沿用当前材质。

## 制作与引用

- 从 715 最初配件材料中复制专用材质，取原区域混合的 A 分支恢复配件自身 UV0 底色。关闭枪身涂层的底色覆盖，将原涂层区域改为金属度 0、粗糙度 0.56。保留原法线、AO、标记、玻璃和发光连接。
- 三类配件的安装座改用独立深色聚合物材质，线性底色为 `(0.022, 0.025, 0.030)`，粗糙度 0.56、金属度 0。原材质槽名保留。
- 复制现有 Chrome 配件静态网格，仅替换材质绑定，保持形状、尺寸、UV、原点和挂点。全息分划使用原 `M_HoloReticle`；未改变准星大小、光心、激光或手电照明参数。
- 独立湿润材质在原外壳遮罩内增加水滴。手电/激光器使用既有顶点 R 遮罩，全息使用原外壳区域遮罩；不会用新的零金属度控制湿润面积。湿润聚合物保留非金属属性，雨滴单独影响粗糙度和法线。
- 当前加载在 `Source/FPSGAME/Weapons/DanWesson715WeaponAssets.h`：主体仍为 `Chrome20260914/SK_DW715_Manny`；上述三种配件在 `AccessoryPolymer20260914/Attachments`，全景红点继续在 `Chrome20260914/Attachments`。
- 独立雨滴表 `AccessoryPolymer20260914/DA_DW715_WetMaterials` 继承 Chrome 的主体/其余配件映射，再追加四组聚合物干湿映射；天气运行入口使用该汇总表。

作者入口：`SourceAssets/DanWesson715AccessoryPolymer20260914/import_polymer.py`。制作记录 `import.json`，日志 `import.log`。源网格、源材质及 Chrome 版本均保留，没有改动共享配件母材质。

## 交付状态

UE 材质与网格变体已保存，作者脚本输出 `DW715_ACCESSORY_POLYMER_IMPORT_COMPLETE`，commandlet 返回 0。必要构建成功（`Result: Succeeded`），输出 `UnrealEditor-FPSGAME-14215057.dll`；日志为作者目录 `build.log`、`build-ubt.log`。未运行游戏、渲染或测试，由用户重启编辑器后自行查看。
