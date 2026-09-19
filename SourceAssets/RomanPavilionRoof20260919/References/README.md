# C4 星图来源

检索和下载日期：2026-09-19。

- 星座坐标和线图：Olaf Frohn / d3-celestial，`data/constellations.lines.json`。
  https://github.com/ofrohn/d3-celestial/blob/master/data/constellations.lines.json
- 恒星星等：同仓库 `data/stars.6.json`；项目资料注明其恒星数据来源为 XHIP: An Extended Hipparcos Compilation, Anderson E., Francis C. (2012), VizieR V/137D。
- 项目许可：BSD-3-Clause；完整版权声明与免责条款保存在 `d3-celestial/LICENSE`，随派生资源分发材料保留。下载的原始 JSON 和说明一并保存。
- 公开源码包含所需两份JSON、许可和本说明；下载的完整上游README保留本机作来源参考，不是制作依赖。
- d3-celestial 的项目说明将其西方星座图来源指向 IAU Constellation page，并说明作者做过部分连线修改。因此本次是复刻该星图版本，不宣称连线是唯一或 IAU 官方规定的版本。
- IAU 资料：https://iauarchive.eso.org/public/themes/constellations/ 。IAU 规定星座边界，没有唯一规定每一条示意连线。

## 本次适配

使用双子、狮子、仙女、英仙、大熊、天鹰、天琴、金牛、天蝎、天鹅、猎户、仙后十二组。
按原始赤经赤纬做各组的局部球心投影（北向上、东向左），保留源数据连线，仅等比缩放到建筑分格，随后贴合穹顶。
不同分格按建筑排布，不代表星座在整片天空中的相互位置。原有白金材质与顶饰为项目自身模型。
星形浮雕尺寸根据星等与局部星间距调整，避免密集星团完全挤成一块；没有新增随机星位或装饰性闭环。

`../previews/C4_constellation_reference.svg` 为同一组数据生成的参考图表，`../C4_constellations.json` 保存原坐标、连线、缩放后坐标和建筑位置。
