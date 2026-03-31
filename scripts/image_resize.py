import os

import numpy as np
from PIL import Image

INPUT_PATH = "../assets/vial/big-size/"
OUTPUT_PATH = "../assets/vial/game/"

WIDTH = 300
HEIGHT = 400

def process_image(input_path, output_path):
    img = Image.open(input_path).resize((WIDTH, HEIGHT))
    img.save(output_path)

def main():
    for filename in os.listdir(INPUT_PATH):
        if filename.endswith(".png"):
            process_image(os.path.join(INPUT_PATH, filename), os.path.join(OUTPUT_PATH, filename))


if __name__ == "__main__":
    main()
