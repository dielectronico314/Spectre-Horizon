import sys
from pathlib import Path
from PIL import Image

def make_thumbs(workspace: Path):
    samples = workspace / "rf-spectrum" / "data" / "samples"
    if not samples.exists():
        print("No samples dir")
        return

    count = 0
    for png in samples.rglob("*_espectrograma.png"):
        thumb_name = png.stem.replace("_espectrograma", "_thumb") + ".png"
        thumb_path = png.with_name(thumb_name)
        if thumb_path.exists():
            continue
        try:
            with Image.open(png) as img:
                img.thumbnail((360, 210))
                img.save(thumb_path, "PNG")
                print(f"Thumb generated: {thumb_path.name}")
                count += 1
        except Exception as e:
            print(f"Error on {png.name}: {e}")
            
    print(f"Done. Generated {count} thumbnails.")

if __name__ == "__main__":
    make_thumbs(Path("/workspace"))
