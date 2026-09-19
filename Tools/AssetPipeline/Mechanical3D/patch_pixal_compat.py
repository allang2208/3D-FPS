"""Apply compatibility fixes required by the deployed 5080 wrapper, without inference."""
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1]) / 'custom_nodes/ComfyUI-Trellis2'
changes = [
    ('trellis2/pipelines/trellis2_image_to_3d.py',
     "        print('Getting Projected Image Cond ...')",
     "        print('Getting Projected Image Cond ...')\n        image_cond_model.naf_tile_factor = 2 if self.low_vram else 1"),
    ('trellis2/pipelines/trellis2_image_to_3d.py',
     '        self.moge_model.eval()',
     '        self.moge_model.enable_pytorch_native_sdpa()\n        self.moge_model.eval()'),
    ('trellis2/trainers/flow_matching/mixins/image_conditioned_proj.py',
     '        for layer_module in self.model.layer:',
     "        layers = self.model.layer if hasattr(self.model, 'layer') else self.model.model.layer\n        for layer_module in layers:"),
]
for relative, old, new in changes:
    path = root / relative
    text = path.read_text(encoding='utf-8')
    if new in text:
        continue
    if text.count(old) != 1:
        raise RuntimeError(f'Wrapper source differs; adapt the patch before applying: {relative}')
    backup = path.with_suffix(path.suffix + '.before_pixal_compat')
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text.replace(old, new), encoding='utf-8')

# MoGe 2 dependency source, installed separately with --no-deps to preserve Torch:
# https://github.com/EasternJournalist/utils3d/tree/3fab839f0be9931dac7c8488eb0e1600c236e183
