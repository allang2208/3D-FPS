# Archived: bronze torch legacy iterations (bronze-torch-legacy-20260918)

- Date: 2026-09-18 / Rule: WORKFLOW.md section 4 / Count: 20
- Moved to: `trash/bronze-torch-legacy-20260918/` (gitignored). Only superseded scripts of the bronze-torch line move here.
- Ignored iteration logs (`*.log`) and preview PNG/OBJ stay in place: they are outside the repo and are still cited as evidence in `SourceAssets/RomanColumn20260915/README.md`.

| File | Bytes | Reason | Replacement |
| --- | ---: | --- | --- |
| build_bronze_torch_20260918.py | 7574 | 青铜火把 v1（柱箍 + 方杆 + 喇叭杯）。被 v3–v8 的重设计取代 | SourceAssets/RomanColumn20260915/build_bronze_torch_v8_20260918.py |
| build_bronze_torch_v2_20260918.py | 5506 | v2 弃案：append_sweep_polyline 扫掠管产生 42 条开放边、帧朝向不可靠 | SourceAssets/RomanColumn20260915/build_bronze_torch_v8_20260918.py |
| build_bronze_torch_v3_20260918.py | 4581 | v3：弯圆柱 + 三支火叉版本，后续按参考图重做成 v4 托架 | SourceAssets/RomanColumn20260915/build_bronze_torch_v8_20260918.py |
| build_bronze_torch_v4_20260918.py | 4944 | v4：按参考图的菱形双板托架版，被 v5/v6/v8 取代 | SourceAssets/RomanColumn20260915/build_bronze_torch_v8_20260918.py |
| build_bronze_torch_v5_20260918.py | 4846 | v5：加长臂 + 主体精修，被 v6/v8 取代 | SourceAssets/RomanColumn20260915/build_bronze_torch_v8_20260918.py |
| build_bronze_torch_v6_20260918.py | 7378 | v6：臂再外伸 + 1024 微法线贴图版；该微法线正是用户报"表面颗粒感"的根因 | SourceAssets/RomanColumn20260915/build_bronze_torch_v8_20260918.py |
| dump_torch_obj.py | 1447 | v1 的 OBJ 导出探针，被后续版本的自查取代 | SourceAssets/RomanColumn20260915/probe_capture_live.py |
| dump_torch_v3.py | 1450 | v3 的 OBJ 导出探针 | SourceAssets/RomanColumn20260915/probe_capture_live.py |
| dump_torch_v4.py | 1450 | v4 的 OBJ 导出探针 | SourceAssets/RomanColumn20260915/probe_capture_live.py |
| dump_torch_v5.py | 1450 | v5 的 OBJ 导出探针 | SourceAssets/RomanColumn20260915/probe_capture_live.py |
| dump_torch_v6.py | 1450 | v6 的 OBJ 导出探针 | SourceAssets/RomanColumn20260915/probe_capture_live.py |
| preview_torch_flame_20260918.py | 1158 | 弃案：视口相机 API set_level_viewport_camera_info 在 Python 里是 no-op，改用临时 SceneCapture | SourceAssets/RomanColumn20260915/probe_capture_live.py |
| probe_bronze_torch_props.py | 1400 | 属性名探针（当时误用 snake_case 全失败，结论已写入 README） | SourceAssets/RomanColumn20260915/probe_torches_placed.py |
| probe_copy_system_renders.py | 2127 | 一次性验证：临时 NiagaraActor 挂副本能出火 | SourceAssets/RomanColumn20260915/README.md |
| probe_torch_v7_api.py | 3096 | v7 期间的 ModelingService API 签名探针 | SourceAssets/RomanColumn20260915/build_bronze_torch_v8_20260918.py |
| probe_torch_v7_result.py | 1077 | v7 材质/网格读回探针 | SourceAssets/RomanColumn20260915/probe_after_build.py |
| retune_torch_flames_20260918.py | 2795 | 火焰改用 pack 原系统 + 抬高原点的临时脚本，被 finalize 版取代 | SourceAssets/RomanColumn20260915/finalize_torch_flame_20260918.py |
| shoot_torch_flame_20260918.py | 3676 | 早期取图脚本，被带激活时序修正的 probe_capture_live.py 取代 | SourceAssets/RomanColumn20260915/probe_capture_live.py |
| try_torchflame_copy_20260918.py | 3130 | 一次性实验：验证项目副本 NS_TorchFlame 能出火；结论已写入 README | SourceAssets/RomanColumn20260915/finalize_torch_flame_20260918.py |
| verify_torch.py | 1328 | v1 的资产读回校验 | SourceAssets/RomanColumn20260915/probe_torches_placed.py |
