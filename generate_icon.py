"""
Generates a sleek, professional SQL Studio icon (.ico and .png)
"""

import os
from PIL import Image, ImageDraw

def create_icon():
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []
    
    for size in sizes:
        w, h = size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Rounded app tile background (#13141f to #1e1f30)
        margin = max(1, int(w * 0.05))
        corner = max(2, int(w * 0.20))
        
        draw.rounded_rectangle(
            [margin, margin, w - margin, h - margin],
            radius=corner,
            fill=(19, 20, 31, 255),
            outline=(251, 191, 36, 255),
            width=max(1, int(w * 0.04))
        )
        
        # Center Database Discs
        cx = w // 2
        dw = int(w * 0.60)
        dh = max(4, int(h * 0.16))
        
        amber = (245, 158, 11, 255)
        gold = (251, 191, 36, 255)
        dark_blue = (30, 32, 48, 255)
        
        y_tiers = [int(h * 0.32), int(h * 0.50), int(h * 0.68)]
        
        for idx, cy in enumerate(y_tiers):
            # Cylinder wall connecting to next tier
            if idx < len(y_tiers) - 1:
                ny = y_tiers[idx + 1]
                draw.rectangle([cx - dw//2, cy, cx + dw//2, ny], fill=dark_blue)
                draw.line([cx - dw//2, cy, cx - dw//2, ny], fill=gold, width=max(1, int(w * 0.03)))
                draw.line([cx + dw//2, cy, cx + dw//2, ny], fill=gold, width=max(1, int(w * 0.03)))
                
            # Disc cap
            draw.ellipse(
                [cx - dw//2, cy - dh//2, cx + dw//2, cy + dh//2],
                fill=gold if idx == 0 else dark_blue,
                outline=gold if idx == 0 else amber,
                width=max(1, int(w * 0.03))
            )
            
        # Top disc golden glow
        if w >= 32:
            top_y = y_tiers[0]
            sw = max(2, int(w * 0.22))
            sh = max(2, int(h * 0.07))
            draw.ellipse([cx - sw//2, top_y - sh//2, cx + sw//2, top_y + sh//2], fill=(255, 255, 255, 220))
            
        images.append(img)
        
    out_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(out_dir, "app_icon.ico")
    png_path = os.path.join(out_dir, "static", "app_icon.png")
    
    # Save multi-res ICO with all sub-images appended
    images[0].save(
        ico_path,
        format="ICO",
        append_images=images[1:],
        sizes=[(im.width, im.height) for im in images]
    )
    # Save main 256x256 PNG
    images[0].save(png_path, format="PNG")
    
    print(f"[Icon] Generated ICO with {len(images)} frames at: {ico_path}")
    print(f"[Icon] Generated PNG at: {png_path}")

if __name__ == "__main__":
    create_icon()

