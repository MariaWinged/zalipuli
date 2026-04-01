import numpy as np
from PIL import Image

INPUT_IMG = "../assets/vial/big-size/back_level.png"
OUTPUT_IMG = "../assets/vial/big-size/back_level_alpha.png"

def process_image(input_path, output_path):
    """
    Transforms a monochrome image based on the following logic:
    - Alpha should be equal to pixel brightness.
    - Pixel should stay white (255, 255, 255).
    - Black pixels (brightness 0) should be transparent black (0, 0, 0, 0).
    """
    try:
        # Open image and convert to grayscale
        img = Image.open(input_path).convert('L')
        gray_array = np.array(img)
        
        # Create an RGBA array (H, W, 4)
        h, w = gray_array.shape
        rgba_array = np.zeros((h, w, 4), dtype=np.uint8)
        
        # Default all colors to white
        rgba_array[:, :, 0] = 255
        rgba_array[:, :, 1] = 255
        rgba_array[:, :, 2] = 255
        # Set alpha to grayscale value
        rgba_array[:, :, 3] = gray_array
        
        # For black pixels (brightness 0), set them to (0, 0, 0, 0)
        black_mask = (gray_array == 0)
        rgba_array[black_mask, 0] = 0
        rgba_array[black_mask, 1] = 0
        rgba_array[black_mask, 2] = 0
        # rgba_array[black_mask, 3] = 0  # This is already 0 from gray_array
        
        # Save output
        output_img = Image.fromarray(rgba_array, 'RGBA')
        output_img.save(output_path)
        print(f"Processed: {input_path} -> {output_path}")
    except Exception as e:
        print(f"Error processing {input_path}: {e}")

def main():
    process_image(INPUT_IMG, OUTPUT_IMG)

if __name__ == "__main__":
    main()
