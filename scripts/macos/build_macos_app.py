#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAUNCH_TEMPLATE = ROOT / "scripts" / "macos" / "launch_hubml.zsh"
APP_NAME = "Hub_ML"
DESKTOP = Path.home() / "Desktop"


def run(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def rounded_rectangle(draw: object, box: tuple[int, int, int, int], radius: int, fill: str) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def draw_icon(png_path: Path) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow is required to build the macOS icon. Run: python -m pip install pillow") from exc

    size = 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    bg = "#0A0C11"
    surface = "#12151D"
    raised = "#1A1F29"
    border = "#313A48"
    accent = "#8B9BFF"
    ready = "#5FAEFF"
    text = "#F1F3F8"
    dim = "#AAB3C2"
    faint = "#6A7382"
    success = "#4FD06A"

    rounded_rectangle(draw, (72, 72, 952, 952), 184, bg)
    rounded_rectangle(draw, (118, 118, 906, 906), 140, surface)
    draw.rounded_rectangle((118, 118, 906, 906), radius=140, outline=border, width=6)

    for offset, color, width in ((0, accent, 22), (42, ready, 12), (78, border, 6)):
        draw.rounded_rectangle(
            (188 + offset, 188 + offset, 836 - offset, 836 - offset),
            radius=92 - offset // 4,
            outline=color,
            width=width,
        )

    rounded_rectangle(draw, (274, 312, 750, 690), 54, raised)
    draw.rounded_rectangle((274, 312, 750, 690), radius=54, outline=border, width=4)

    font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    font_path = next((path for path in font_candidates if Path(path).exists()), None)
    if font_path:
        font_big = ImageFont.truetype(font_path, 168)
        font_small = ImageFont.truetype(font_path, 48)
        font_meta = ImageFont.truetype(font_path, 34)
    else:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_meta = ImageFont.load_default()

    draw.text((512, 486), "ML", fill=text, font=font_big, anchor="mm")
    draw.text((512, 622), "Hub_ML", fill=dim, font=font_small, anchor="mm")
    draw.text((512, 258), "LOCAL", fill=faint, font=font_meta, anchor="mm")

    draw.ellipse((690, 234, 732, 276), fill=success)
    draw.ellipse((704, 248, 718, 262), fill=text)

    image.save(png_path)


def build_icon(app_contents: Path, build_dir: Path) -> None:
    icon_png = build_dir / "Hub_ML_1024.png"
    iconset = build_dir / "Hub_ML.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    draw_icon(icon_png)

    sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for filename, size in sizes.items():
        target = iconset / filename
        run(["sips", "-z", str(size), str(size), str(icon_png), "--out", str(target)])

    resources = app_contents / "Resources"
    resources.mkdir(parents=True, exist_ok=True)
    run(["iconutil", "-c", "icns", str(iconset), "-o", str(resources / "AppIcon.icns")])
    shutil.copy2(icon_png, resources / "AppIcon.png")


def write_plist(app_contents: Path) -> None:
    payload = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": APP_NAME,
        "CFBundleExecutable": APP_NAME,
        "CFBundleIconFile": "AppIcon",
        "CFBundleIdentifier": "local.hubml.app",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.2.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
    }
    with (app_contents / "Info.plist").open("wb") as handle:
        plistlib.dump(payload, handle)


def write_launcher(app_contents: Path, project_root: Path) -> None:
    launcher = LAUNCH_TEMPLATE.read_text(encoding="utf-8")
    launcher = launcher.replace("__HUBML_PROJECT_ROOT__", str(project_root))

    macos_dir = app_contents / "MacOS"
    macos_dir.mkdir(parents=True, exist_ok=True)
    executable = macos_dir / APP_NAME
    executable.write_text(launcher, encoding="utf-8")
    executable.chmod(0o755)


def build_app(output_dir: Path) -> Path:
    app_path = output_dir / f"{APP_NAME}.app"
    build_dir = ROOT / "build" / "macos_app"

    if app_path.exists():
        shutil.rmtree(app_path)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    app_contents = app_path / "Contents"
    app_contents.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    write_plist(app_contents)
    write_launcher(app_contents, ROOT)
    build_icon(app_contents, build_dir)

    return app_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Hub_ML.app for macOS.")
    parser.add_argument(
        "--output-dir",
        default=str(DESKTOP),
        help="Directory where Hub_ML.app will be created. Default: ~/Desktop.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    app_path = build_app(output_dir)
    print(app_path)


if __name__ == "__main__":
    main()
