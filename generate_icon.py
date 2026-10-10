"""
Generates a sleek, professional Beekeeper Studio icon (.ico and .png)
"""

import os
from PIL import Image, ImageDraw

def create_icon():
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []
    
    for size in sizes:
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        w, h = size
        
        # Outer rounded background (Dark Navy/Charcoal)
        margin = int(w * 0.04)
        corner = int(w * 0.22)
        bg_color = (24, 25, 38, 255) # #181926
        border_color = (251, 191, 36, 255) # #fbbf24 Gold
        
        # Background plate
        draw.rounded_rectangle(
            [margin, margin, w - margin, h - margin],
            radius=corner,
            fill=bg_color,
            outline=border_color,
            width=max(1, int(w * 0.035))
        )
        
        # Database Discs / Cylinder (Gold & Amber gradient style)
        cx = w // 2
        dw = int(w * 0.55)
        dh = int(h * 0.16)
        
        disc_color = (245, 158, 11, 255) # Amber
        highlight = (251, 191, 36, 255) # Gold
        disc_bg = (34, 36, 54, 255)
        
        # 3 Database layers
        y_positions = [int(h * 0.30), int(h * 0.48), int(h * 0.66)]
        
        for idx, cy in enumerate(y_positions):
            # Disc rim
            draw.ellipse(
                [cx - dw//2, cy - dh//2, cx + dw//2, cy + dh//2],
                fill=highlight if idx == 0 else disc_bg,
                outline=disc_color,
                width=max(1, int(w * 0.025))
            )
            
            # Cylinder body
            if idx < len(y_positions) - 1:
                next_y = y_positions[idx + 1]
                draw.rectangle(
                    [cx - dw//2, cy, cx + dw//2, next_y],
                    fill=disc_bg,
                    outline=None
                )
                draw.line([cx - dw//2, cy, cx - dw//2, next_y], fill=disc_color, width=max(1, int(w * 0.025)))
                draw.line([cx + dw//2, cy, cx + dw//2, next_y], fill=disc_color, width=max(1, int(w * 0.025)))
                
        # Center Bee / Spark accent on top disc
        top_y = y_positions[0]
        sw = int(w * 0.16)
        draw.ellipse([cx - sw//2, top_y - sw//4, cx + sw//2, top_y + sw//4], fill=(255, 255, 255, 220))
        
        images.append(img)
        
    out_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(out_dir, "app_icon.ico")
    png_path = os.path.join(out_dir, "static", "app_icon.png")
    
    # Save multi-res ICO
    images[0].save(ico_path, format="ICO", sizes=sizes)
    # Save main PNG
    images[0].save(png_path, format="PNG")
    
    print(f"[Icon] Generated icon at: {ico_path}")
    print(f"[Icon] Generated PNG at: {png_path}")

if __name__ == "__main__":
    create_icon()
