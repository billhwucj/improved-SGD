import os

folder = "./data/gt"  # change to the directory containing your screenshots

for filename in os.listdir(folder):
    # Only handle .png files with at least one space
    if filename.endswith(".png") and " " in filename:
        base = filename.split(" ")[0]  # keep everything before the first space
        new_name = base + ".png"

        old_path = os.path.join(folder, filename)
        new_path = os.path.join(folder, new_name)

        if filename != new_name:
            print(f"Renaming: {filename} -> {new_name}")
            os.rename(old_path, new_path)
