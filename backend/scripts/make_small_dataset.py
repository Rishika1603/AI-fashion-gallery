import os
import shutil
import random

SRC = "/home/rishika-vishwakarma/Projects/AI-fashion-gallery/Clothes_Dataset"
DST = "/home/rishika-vishwakarma/Projects/AI-fashion-gallery/Clothes_Dataset_small"
SAMPLE_PER_CATEGORY = 10
SEED = 42

random.seed(SEED)

categories = []
for name in os.listdir(SRC):
    path = os.path.join(SRC, name)
    if os.path.isdir(path):
        categories.append(name)

print(f"Found {len(categories)} categories under {SRC}")

for category in categories:
    src_dir = os.path.join(SRC, category)
    dst_dir = os.path.join(DST, category)
    os.makedirs(dst_dir, exist_ok=True)
    files = [f for f in os.listdir(src_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    sample = files[:SAMPLE_PER_CATEGORY]
    for file_name in sample:
        shutil.copy2(os.path.join(src_dir, file_name), os.path.join(dst_dir, file_name))
    print(f"Copied {len(sample)} files to {dst_dir}")

print("Small dataset ready under:", DST)
