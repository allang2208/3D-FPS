"""Export a 10 FPS gunplay capture without shortening gaps in Frame_NNNN.png.

Usage:
    python render_gunplay_preview.py Saved/GunplayUpgrade/fps60-final
    python render_gunplay_preview.py path/to/Frames --output-dir path/to/Preview

The audit captures at 10 Hz regardless of the game FPS label. Missing indices hold
the preceding image; missing leading indices hold the earliest available image.
Source screenshots are read only. Pass --overwrite to replace existing exports.
Requires Pillow; ffmpeg comes from --ffmpeg, PATH, or imageio_ffmpeg.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont, ImageOps


FPS = 10
FRAME_PATTERN = re.compile(r"Frame_(\d+)\.png", re.IGNORECASE)
STILL_CHOICES = {
    "hip": ("Hip / recovered", ("00_Hip.png", "10_Final_Recovered.png", "00_Equip.png")),
    "ads": ("ADS alignment", ("01_ADS_Aligned.png",)),
    "fire": ("ADS fire / muzzle FX", ("02_ADS_Fire_FX.png", "03_Burst_Smoke.png")),
    "reload": ("Empty reload / magazine seat", ("07_EmptyReload_Charge.png", "04_Reload_Sprint.png", "05_Reload_Slide.png")),
}


def find_ffmpeg(explicit: str | None) -> str:
    if explicit:
        executable = Path(explicit).expanduser().resolve()
        if not executable.is_file():
            raise ValueError(f"ffmpeg does not exist: {executable}")
        return str(executable)
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        import imageio_ffmpeg
    except ImportError as error:
        raise ValueError("Install imageio-ffmpeg or specify --ffmpeg PATH.") from error
    return imageio_ffmpeg.get_ffmpeg_exe()


def image_size(path: Path, max_width: int) -> tuple[int, int]:
    with Image.open(path) as source:
        ratio = min(1.0, max_width / source.width)
        return max(2, int(source.width * ratio) // 2 * 2), max(2, int(source.height * ratio) // 2 * 2)


def load_rgb(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        return ImageOps.pad(source.convert("RGB"), size, method=Image.Resampling.LANCZOS, color=(15, 18, 22))


def font(size: int) -> ImageFont.ImageFont:
    for filename in ("C:/Windows/Fonts/segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(filename, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def select_stills(directory: Path, args: argparse.Namespace) -> list[tuple[str, Path]]:
    selected = []
    for key, (title, choices) in STILL_CHOICES.items():
        override = getattr(args, key)
        if override:
            candidate = Path(override)
            candidate = candidate if candidate.is_absolute() else directory / candidate
            if not candidate.is_file():
                raise ValueError(f"Missing --{key} screenshot: {candidate}")
        else:
            candidate = next((directory / name for name in choices if (directory / name).is_file()), None)
            if candidate is None:
                raise ValueError(f"No {key} screenshot in {directory}; specify --{key} FILE.")
        selected.append((getattr(args, f"{key}_title") or title, candidate.resolve()))
    return selected


def create_collage(stills: list[tuple[str, Path]], target: Path) -> None:
    tile = (640, 360)
    caption_height, gap = 48, 8
    canvas = Image.new("RGB", (tile[0] * 2 + gap, (tile[1] + caption_height) * 2 + gap), (15, 18, 22))
    draw = ImageDraw.Draw(canvas)
    for index, (title, path) in enumerate(stills):
        x = (index % 2) * (tile[0] + gap)
        y = (index // 2) * (tile[1] + caption_height + gap)
        canvas.paste(load_rgb(path, tile), (x, y))
        draw.text((x + 10, y + tile[1] + 4), title, font=font(18), fill=(238, 241, 244))
        draw.text((x + 10, y + tile[1] + 27), path.name, font=font(13), fill=(158, 169, 178))
    canvas.save(target, optimize=True)


def encode_mp4(ffmpeg: str, timeline: list[Path], target: Path, size: tuple[int, int]) -> None:
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24",
               "-video_size", f"{size[0]}x{size[1]}", "-framerate", str(FPS), "-i", "pipe:0", "-an",
               "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-threads", "2",
               "-movflags", "+faststart", str(target)]
    with tempfile.TemporaryFile() as error_log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=error_log)
        try:
            cached_path, cached_frame = None, None
            for path in timeline:
                if path != cached_path:
                    cached_frame = load_rgb(path, size).tobytes()
                    cached_path = path
                process.stdin.write(cached_frame)
            process.stdin.close()
            return_code = process.wait()
            if return_code:
                error_log.seek(0)
                raise RuntimeError(error_log.read().decode("utf-8", errors="replace"))
        except BaseException:
            if process.poll() is None:
                process.kill()
            process.wait()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("capture_dir", type=Path, help="Saved/GunplayUpgrade/<label>, or its Frames directory")
    parser.add_argument("--output-dir", type=Path, help="Default: <label>/Preview")
    parser.add_argument("--ffmpeg", help="Absolute ffmpeg executable path")
    parser.add_argument("--width", type=int, default=1280, help="Maximum MP4 width (default: 1280)")
    parser.add_argument("--gif-width", type=int, default=720, help="Maximum GIF width (default: 720)")
    parser.add_argument("--gif-colors", type=int, default=96, help="GIF palette size, 4-256 (default: 96)")
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--end-index", type=int, help="Inclusive final index; default: last available frame")
    parser.add_argument("--overwrite", action="store_true")
    for key in STILL_CHOICES:
        parser.add_argument(f"--{key}", help=f"Override {key} panel with an absolute path or a capture filename")
        parser.add_argument(f"--{key}-title", help=f"Override the {key} panel caption to match the actual selected pose")
    args = parser.parse_args()
    if min(args.width, args.gif_width) < 2 or not 4 <= args.gif_colors <= 256 or args.start_index < 0:
        parser.error("Widths must be at least 2, GIF colors 4-256, and start index nonnegative.")

    directory = args.capture_dir.expanduser().resolve()
    if directory.name.lower() == "frames":
        directory = directory.parent
    frame_directory = directory / "Frames"
    frames = {}
    for path in sorted(frame_directory.glob("*.png")):
        match = FRAME_PATTERN.fullmatch(path.name)
        if match:
            index = int(match.group(1))
            if index in frames:
                raise ValueError(f"Duplicate frame number {index}: {frames[index]} and {path}")
            frames[index] = path
    indices = sorted(frames)
    if not indices:
        parser.error(f"No Frame_NNNN.png files in {frame_directory}")
    end_index = args.end_index if args.end_index is not None else indices[-1]
    if end_index < args.start_index:
        parser.error("End index precedes start index.")
    timeline = [frames[indices[max(0, bisect_right(indices, index) - 1)]] for index in range(args.start_index, end_index + 1)]
    missing = [index for index in range(args.start_index, end_index + 1) if index not in frames]
    stills = select_stills(directory, args)
    ffmpeg = find_ffmpeg(args.ffmpeg)
    output_directory = (args.output_dir or directory / "Preview").expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    names = ("gunplay_preview.mp4", "gunplay_preview.gif", "gunplay_comparison.png", "gunplay_preview.json")
    if not args.overwrite:
        existing = [str(output_directory / name) for name in names if (output_directory / name).exists()]
        if existing:
            parser.error("Existing exports; choose another --output-dir or pass --overwrite: " + ", ".join(existing))
    size = image_size(timeline[0], args.width)
    print(f"{len(frames)} source frames -> {len(timeline)} samples at {FPS} FPS; holding {len(missing)} missing indices.", flush=True)
    with tempfile.TemporaryDirectory(prefix="gunplay-preview-", dir=output_directory) as temporary:
        staging = Path(temporary)
        encode_mp4(ffmpeg, timeline, staging / names[0], size)
        gif_width = min(size[0], args.gif_width)
        filters = (f"fps={FPS},scale={gif_width}:-1:flags=lanczos,split[a][b];"
                   f"[a]palettegen=max_colors={args.gif_colors}:stats_mode=diff[p];"
                   "[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle")
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(staging / names[0]),
                        "-filter_complex_threads", "1", "-filter_complex", filters, "-loop", "0", str(staging / names[1])], check=True)
        create_collage(stills, staging / names[2])
        report = {
            "capture_directory": str(directory), "capture_fps": FPS, "output_fps": FPS,
            "source_frame_count": len(frames), "start_index": args.start_index, "end_index": end_index,
            "output_frame_count": len(timeline), "duration_seconds": len(timeline) / FPS,
            "held_missing_indices": missing, "gap_policy": "Hold preceding frame; use earliest frame before first available index.",
            "video_size": list(size), "gif_width": gif_width, "gif_colors": args.gif_colors,
            "panels": [{"title": title, "source": str(path)} for title, path in stills],
            "outputs": {name: str(output_directory / name) for name in names},
            "note": "Presentation export only; source run assertions and visual acceptance remain separate.",
        }
        (staging / names[3]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for name in names:
            (staging / name).replace(output_directory / name)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
