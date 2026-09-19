# Phantom rear grip — Pixal3D candidate

Generated on RTX 5080 from the user-provided screenshot, 2026-09-13.

- Model: TencentARC/Pixal3D (installed wrapper alias TencentARC/Pixal3D-T).
- Single-view input cropped by ComfyUI ImageCrop and background removed by Trellis2PreProcessImage. No invented reference views.
- 1024_cascade, steps 16/32/24, seed 91301, sparse structure resolution 32, 4096 texture export, 500000 target faces. MultiViewRefiner was not used with this single image.
- Successful prompt: 65d39e4a-cd21-48b0-b3fd-d7e9727b1c05; server reported 155.26 seconds for the successful generation run. First-run dependency repairs took additional time.
- `textured_master_00001_.glb`: generated textured model. `raw_00001_.glb`: raw generated geometry.
- `PhantomRearGrip_Pixal_Editable.blend`: model and preview studio. Preview transforms only; generated geometry and materials were retained.
- `angle.png`, `front.png`, `back.png`, `side.png`: actual Blender renders requested by the user.
- Visible limitations: warped/thin internal ribs, softened edges, missing fine grip texture; hidden side is inferred from one view.
- Candidate only; no UE import or gameplay tests performed. User reviews/tests the asset.
- Reference supplied by user; third-party reference rights are not established by generation.

## Runtime repairs used

MoGe 2 required utils3d 1.3 from commit 3fab839f0be9931dac7c8488eb0e1600c236e183. MoGe now enables its own native SDPA, and the Pixal DINO feature extractor supports the installed Transformers encoder layout. Reusable patch: `Tools/AssetPipeline/Mechanical3D/patch_pixal_compat.py`.

NAF indirectly requires NATTEN despite the wrapper itself not importing it. Matching Windows cp311/Torch 2.9.1 NATTEN was unavailable in the wrapper wheels; this run uses NAF's original learned weights with a local chunked PyTorch neighborhood-attention implementation. Source and patch are retained under `naf_source/NAF-main`; remote deployed copy is `C:/Users/WINDOWS/.cache/torch/hub/valeoai_NAF_torch_20260913`.

For 16 GB VRAM, low_vram uses the wrapper's existing `naf_tile_factor=2` streaming path. Upstream documents this tiled feature calculation as near-equivalent, not bit-identical, to the full-frame calculation. No numerical-equivalence testing was performed.

NAF upstream: https://github.com/valeoai/NAF
MoGe 2 dependency declaration: https://github.com/microsoft/MoGe/blob/b942f00bdc2a2a23ebb474fbe034d487e6dcceec/pyproject.toml
