from PIL import Image, ImageDraw, ImageFont

def create_logo():
    width, height = 320, 80
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Compass leaf emblem on the left
    cx, cy = 40, 40
    r = 28

    # Outer subtle circle
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(13, 31, 35, 230), outline=(20, 184, 166, 255), width=2)
    draw.ellipse([cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4], outline=(16, 185, 129, 120), width=1)

    leaf_points = [
        (cx - 10, cy + 12),
        (cx - 14, cy - 2),
        (cx - 2, cy - 16),
        (cx + 16, cy - 16),
        (cx + 16, cy + 2),
        (cx + 2, cy + 14),
    ]
    draw.polygon(leaf_points, fill=(16, 185, 129, 255))
    draw.line([(cx - 10, cy + 12), (cx + 14, cy - 14)], fill=(255, 255, 255, 200), width=2)

    try:
        font_large = ImageFont.truetype("arialbd.ttf", 32)
        font_small = ImageFont.truetype("arial.ttf", 10)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((78, 18), "Explore", fill=(248, 250, 252, 255), font=font_large)
    draw.text((195, 18), "Mate", fill=(20, 184, 166, 255), font=font_large)
    draw.text((80, 52), "ADAPTIVE TRAVEL & HERITAGE GUIDE", fill=(148, 163, 184, 255), font=font_small)

    image.save("assets/logo.png", "PNG")
    image.save("static/logo.png", "PNG")
    print("Logo saved to assets/logo.png and static/logo.png")

if __name__ == "__main__":
    create_logo()
