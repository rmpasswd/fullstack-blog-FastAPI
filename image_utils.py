import uuid

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

PROFILE_PICS_DIR = Path("media/profile_pics")


def process_profile_pic(image_content: bytes) -> str:
    with Image.open(BytesIO(image_content)) as original:
        img = ImageOps.exif_transpose(original)
        img = ImageOps.fit(img,(300, 300), method= Image.Resampling.LANCZOS)
        
        # some formats cannot process transparency
        if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

        # assign a random filename
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = PROFILE_PICS_DIR / filename
        PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)
        img.save(filepath, "JPEG", quality=85, optimize=True)
        
    return filename



def delete_profilepic(filename: str | None) -> None:
    if filename is None:
        return # why is this necessary?
    
    filepath = PROFILE_PICS_DIR / filename
    if filepath.exists():
        filepath.unlink()


    