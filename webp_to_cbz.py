import os
import zipfile
from pathlib import Path
import shutil

def convert_folder_to_cbz(folder_path):
    # Create output folder at parent level
    parent_folder = os.path.dirname(folder_path)
    output_folder = os.path.join(parent_folder, "CBZ_Output")
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all subfolders in the main folder
    subfolders = [f for f in Path(folder_path).iterdir() if f.is_dir()]
    
    if not subfolders:
        print("No subfolders found. Processing the main folder as a single chapter.")
        convert_images_to_cbz(folder_path, output_folder)
        return
    
    # Process each subfolder (chapter)
    for subfolder in subfolders:
        convert_images_to_cbz(subfolder, output_folder)
    
    # Create a parent CBZ containing all chapters
    create_parent_cbz(output_folder, folder_path)

def convert_images_to_cbz(folder_path, output_folder):
    # Get all webp and jpg files in the folder
    image_files = list(Path(folder_path).glob('*.webp')) + list(Path(folder_path).glob('*.jpg'))
    
    if not image_files:
        print(f"No image files found in {folder_path}")
        return
    
    # Create a CBZ file with the same name as the folder
    folder_name = os.path.basename(folder_path)
    cbz_filename = f"{folder_name}.cbz"
    cbz_path = os.path.join(output_folder, cbz_filename)
    
    # Create a ZIP file (CBZ)
    with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as cbz:
        for image_file in image_files:
            # Add each image file to the CBZ archive
            cbz.write(image_file, arcname=image_file.name)
    
    print(f"Successfully created {cbz_filename} with {len(image_files)} image files.")

def create_parent_cbz(output_folder, source_folder):
    # Get all CBZ files in the output folder
    cbz_files = list(Path(output_folder).glob('*.cbz'))
    
    if not cbz_files:
        return
    
    # Create a parent CBZ file
    folder_name = os.path.basename(source_folder)
    parent_cbz_filename = f"{folder_name}_complete.cbz"
    parent_cbz_path = os.path.join(output_folder, parent_cbz_filename)
    
    with zipfile.ZipFile(parent_cbz_path, 'w', zipfile.ZIP_DEFLATED) as parent_cbz:
        for cbz_file in cbz_files:
            parent_cbz.write(cbz_file, arcname=cbz_file.name)
    
    print(f"Successfully created parent CBZ file: {parent_cbz_filename}")

if __name__ == "__main__":
    # Using forward slashes or raw string for Windows path
    convert_folder_to_cbz(r"C:\Users\leehe\Documents\Komga Src\Test\mangadex\Garuru Girl") 