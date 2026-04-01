import os

import numpy as np
from PIL import Image

INPUT_PATH = "../assets/vial/big-size/empty.png"
DIFF_PATH = "../assets/vial/big-size/filled.png"
OUTPUT_PATH = "../assets/vial/big-size/back_level.png"


def process_image(input_path, input_diff_path, output_path):
    img = Image.open(input_path).convert("L")
    diff = Image.open(input_diff_path).convert("L")

    mix_array = np.array(img)
    front_array = np.array(diff)

    mask = front_array > mix_array
    front_array[mask] = mix_array[mask]


    output_array = (1 - (1 - mix_array / 255) / (1 - front_array / 225)) * 255
    output = Image.fromarray(output_array).convert("L")

    output.save(output_path)

def main():
    process_image(INPUT_PATH, DIFF_PATH, OUTPUT_PATH)


if __name__ == "__main__":
    main()
