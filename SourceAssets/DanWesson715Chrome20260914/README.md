# 715 Chrome 作者入口

对应说明：`Docs/Weapons/dan-wesson715-chrome-20260914.md`。

- `read_material_source.py` 读取用户下载的官方 Chromium/Silver 图与参数，供材质适配使用；不改变源包。
- `import_chrome.py` 复制官方 Chromium 父链中的材质/金属函数，接入现有结构法线和雨滴，保存独立材质实例及主枪/配件副本。
- 输入：`SubstrateMaterials` 官方包、`DanWesson715Detail20260914/import.json`、`DanWesson715Mirror20260914/import.json`、`WeatherNatural20260912/WeaponBeads.hlsl`。
- 输出：`/Game/Weapons/DanWesson715/Chrome20260914`；具体资源记录在 `import.json`。
- 编辑器中可调整三个 `MI_DW715_Chrome_*` 的 `Chrome Roughness` 和 `Structural Roughness Amount`。`Normal Map` 是本枪结构法线，不替换为通用砂喷或石材法线。
- 不新增模型重建；可编辑几何继续使用 Detail/Mirror 作者源。原始下载包和历史版本保留。
- 必要的作者命令使用 UnrealEditor-Cmd Python commandlet；不启动 PIE、截图或渲染。未进行游戏或视觉测试。

官方来源：https://www.fab.com/listings/1272587c-1431-4878-9d78-2a6b84ebe839 。原包及派生二进制仅保留本机，按原许可使用。
