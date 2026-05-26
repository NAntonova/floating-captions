import os
import sys
import subprocess
from PIL import Image, ImageDraw

def main():
    if len(sys.argv) < 2:
        print("Usage: python make_icns.py <path_to_png>")
        sys.exit(1)
        
    png_path = sys.argv[1]
    if not os.path.exists(png_path):
        print(f"File not found: {png_path}")
        sys.exit(1)
        
    print(f"Processing image: {png_path}")
    img = Image.open(png_path).convert("RGBA")
    
    # 1. Flood fill from the 4 corners to make the black background transparent
    width, height = img.size
    # We will use a threshold of 20 to catch near-black compression artifacts
    thresh = 20
    
    # Target color is fully transparent
    target_color = (0, 0, 0, 0)
    
    # Perform flood fill from all 4 corners
    for start_point in [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]:
        ImageDraw.floodfill(img, start_point, target_color, thresh=thresh)
        
    # Save the processed image temporarily
    temp_png = "temp_transparent.png"
    img.save(temp_png)
    print("Background made transparent.")
    
    # 2. Create the macOS iconset directory
    iconset_dir = "icon.iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    
    # Target sizes defined by Apple for macOS app icons
    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png")
    ]
    
    # Resize and save images into icon.iconset
    for size, name in sizes:
        resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
        resized_img.save(os.path.join(iconset_dir, name))
        
    print(f"Created all resized PNGs in {iconset_dir}.")
    
    # 3. Compile the iconset into a .icns file using iconutil
    icns_path = "icon.icns"
    try:
        subprocess.run(["iconutil", "-c", "icns", iconset_dir], check=True)
        print(f"Successfully generated {icns_path}")
    except Exception as e:
        print(f"Error compiling iconset: {e}")
        sys.exit(1)
        
    # Cleanup temporary files
    if os.path.exists(temp_png):
        os.remove(temp_png)
        
    # Clean up iconset directory
    for size, name in sizes:
        p = os.path.join(iconset_dir, name)
        if os.path.exists(p):
            os.remove(p)
    try:
        os.rmdir(iconset_dir)
        print("Cleaned up temporary iconset files.")
    except Exception:
        pass
        
    print("Done! icon.icns is ready.")

if __name__ == "__main__":
    main()
