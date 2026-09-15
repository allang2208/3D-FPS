"""Produce the user-authorized local alpha cutouts for the three HUD entries."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "SourceAssets/PanelNavigation20260915/SubjectOnly"
RUNTIME = ROOT / "Content/ColdSteelUI/Icons/Navigation"


def main():
    session = new_session("isnet-general-use", providers=["CPUExecutionProvider"])
    RUNTIME.mkdir(parents=True, exist_ok=True)
    records = []
    for name in ("status", "backpack", "skills"):
        image = Image.open(SOURCE / f"{name}_generated_rgb.png").convert("RGB")
        mask = remove(image, session=session, only_mask=True).convert("L")
        # Discard residual background confidence before feathering the cut edge.
        alpha = np.asarray(mask).copy()
        alpha[alpha < 24] = 0
        alpha[alpha > 232] = 255
        mask = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(.45))
        rgba = image.convert("RGBA")
        rgba.putalpha(mask)
        rgba.save(SOURCE / f"{name}_cutout.png")
        bounds = mask.getbbox()
        if bounds is None:
            raise RuntimeError(f"Background model produced no subject for {name}")
        subject = rgba.crop(bounds)
        # Match the three subjects' visual footprint; retain breathing room for hover.
        subject.thumbnail((430, 430), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        canvas.alpha_composite(subject, ((512-subject.width)//2, (512-subject.height)//2))
        output = RUNTIME / f"{name}_subject.png"
        canvas.save(output)
        records.append({"name": name, "source": str(SOURCE / f"{name}_generated_rgb.png"),
                        "cutout": str(SOURCE / f"{name}_cutout.png"), "runtime": str(output),
                        "size": [512, 512], "mode": "RGBA", "subject_bounds": list(bounds)})
        print(f"Exported {name}: RGBA 512x512 -> {output}", flush=True)
    (SOURCE / "local-cutout.json").write_text(json.dumps({
        "authorization": "User explicitly requested local background removal and game integration.",
        "method": "rembg isnet-general-use CPU; alpha cleanup; proportional layout in transparent canvas",
        "assets": records,
        "runtime_testing": "Not requested; not performed."
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
