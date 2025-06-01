import os
import subprocess
import re
from pathlib import Path
import shutil
import sys
import zipfile
import json
import datetime
from urllib.parse import urlparse

def get_valid_input(prompt, validation_func):
    while True:
        user_input = input(prompt).strip()
        if validation_func(user_input):
            return user_input
        print("Invalid input. Please try again.")

def validate_manga_name(name):
    return bool(name.strip())

def validate_manga_url(url):
    return bool(url.strip())

def validate_manga_type(manga_type):
    return manga_type.lower() in ['manga', 'doujin']

def validate_resource_type(choice):
    return choice in ['1', '2']

def get_resource_type():
    """Display menu and get resource type selection"""
    print("\nSelect Resource Type:")
    print("1. Manga")
    print("2. Doujin/One-shot")
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if validate_resource_type(choice):
            return "Manga" if choice == "1" else "Doujin"
        print("Invalid choice. Please enter 1 or 2.")

def extract_chapter_number(folder_name):
    """Extract chapter number from various common formats"""
    # Try different patterns
    patterns = [
        r'c(\d+)',  # c001, c1, etc.
        r'ch(\d+)',  # ch001, ch1, etc.
        r'chapter\s*(\d+)',  # chapter 1, chapter001, etc.
        r'episode\s*(\d+)',  # episode 1, episode001, etc.
        r'(\d+)(?:\s*-\s*.*)?$'  # Just a number at the end
    ]
    
    for pattern in patterns:
        match = re.search(pattern, folder_name.lower())
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None

def extract_chapter_info(folder_name):
    """Extract chapter number, volume, and chapter name from folder name"""
    # Try to extract volume and chapter number
    volume_match = re.search(r'v(\d+)', folder_name.lower())
    chapter_match = re.search(r'c(\d+)', folder_name.lower())
    
    volume = volume_match.group(1) if volume_match else None
    chapter = chapter_match.group(1) if chapter_match else None
    
    # Extract chapter name (everything after the chapter number)
    if chapter_match:
        chapter_name = folder_name[chapter_match.end():].strip(' _-')
    else:
        chapter_name = None
    
    return volume, chapter, chapter_name

def get_safe_folder_name(folder_name, counter=None):
    """Create a safe folder name from potentially gibberish input"""
    # Remove any invalid characters
    safe_name = sanitize_filename(folder_name)
    # If the name is too long, truncate it
    if len(safe_name) > 50:
        safe_name = safe_name[:50]
    # If the name is empty after sanitization, use a default
    if not safe_name:
        safe_name = "Chapter"
    # Add counter if provided
    if counter is not None:
        safe_name = f"{safe_name}_{counter}"
    return safe_name

def rename_chapter_folders(temp_folder):
    """Rename chapter folders to a standardized format (Chapter X)"""
    folders = list(Path(temp_folder).iterdir())
    # Sort folders to ensure consistent numbering
    folders.sort()
    
    for folder in folders:
        if folder.is_dir():
            chapter_num = extract_chapter_number(folder.name)
            if chapter_num is not None:
                new_name = f"Chapter {chapter_num}"
                new_path = folder.parent / new_name
                try:
                    folder.rename(new_path)
                except FileExistsError:
                    # If folder already exists, append a number
                    counter = 1
                    while True:
                        new_name = f"Chapter {chapter_num}_{counter}"
                        new_path = folder.parent / new_name
                        if not new_path.exists():
                            folder.rename(new_path)
                            break
                        counter += 1

def convert_folder_to_cbz(folder_path, output_folder, base_name=None, chapter_number=None):
    """Convert a folder of images to CBZ format"""
    # Get all image files in the folder
    image_files = []
    for ext in ['*.webp', '*.jpg', '*.jpeg', '*.png']:
        image_files.extend(list(Path(folder_path).glob(ext)))
    
    if not image_files:
        print(f"No image files found in {folder_path}")
        return
    
    # Create a CBZ file with the appropriate name
    if base_name and chapter_number is not None:
        # For multiple links, use the format "basename Chapter n"
        cbz_filename = f"{base_name} Chapter {chapter_number}.cbz"
    else:
        # For single links, use the folder name
        folder_name = os.path.basename(folder_path)
        cbz_filename = f"{folder_name}.cbz"
    
    cbz_path = os.path.join(output_folder, cbz_filename)
    
    # Create a ZIP file (CBZ)
    with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as cbz:
        for image_file in image_files:
            # Add each image file to the CBZ archive
            cbz.write(image_file, arcname=image_file.name)
    
    print(f"Successfully created {cbz_filename} with {len(image_files)} image files.")

def download_manga(url, temp_folder):
    """Download manga using gallery-dl"""
    try:
        # Create temp folder if it doesn't exist
        os.makedirs(temp_folder, exist_ok=True)
        
        # Run gallery-dl command with language parameter
        cmd = ['gallery-dl', '-d', temp_folder, '-o', 'lang=en', url]
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading manga: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def find_chapter_folders(root_folder):
    """Recursively find all chapter folders in the directory structure"""
    chapter_folders = []
    for path in Path(root_folder).rglob('*'):
        if path.is_dir():
            # Check if this is a chapter folder by looking for image files
            has_images = any(path.glob('*.webp')) or any(path.glob('*.jpg')) or any(path.glob('*.jpeg')) or any(path.glob('*.png'))
            if has_images:
                chapter_folders.append(path)
    return chapter_folders

def sanitize_filename(filename):
    """Replace invalid filename characters with safe alternatives"""
    # Replace invalid characters with a hyphen
    invalid_chars = r'[\\/*?:"<>|]'
    sanitized = re.sub(invalid_chars, '-', filename)
    # Remove any leading/trailing spaces and hyphens
    sanitized = sanitized.strip(' -')
    return sanitized

def save_metadata(export_path, manga_name, manga_url, is_multiple=False, metadata=None):
    """Save manga metadata including the URL for future updates"""
    if is_multiple:
        # For multiple links, update the existing metadata
        if metadata is None:
            metadata = {
                "resources": [],
                "last_updated": datetime.datetime.now().isoformat()
            }
        
        # Add the new resource to the metadata
        metadata["resources"].append({
            "name": manga_name,
            "url": manga_url
        })
    else:
        # For single links, create new metadata
        metadata = {
            "name": manga_name,
            "url": manga_url,
            "last_updated": datetime.datetime.now().isoformat()
        }
    
    metadata_path = os.path.join(export_path, "metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

def validate_url(url):
    """Validate if the input is a valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_single_link():
    """Get a single link from user"""
    while True:
        url = input("Enter the URL: ").strip()
        if validate_url(url):
            return url
        print("Invalid URL format. Please enter a valid URL.")

def get_multiple_links():
    """Get multiple links from user, either one by one or semicolon-separated"""
    print("\nEnter manga URLs:")
    print("You can either:")
    print("1. Enter URLs one by one (type 'done' when finished)")
    print("2. Paste multiple URLs separated by semicolons (;)")
    print("==============================")
    
    while True:
        input_method = input("Choose input method (1 or 2): ").strip()
        if input_method not in ['1', '2']:
            print("Invalid choice. Please enter 1 or 2.")
            continue
            
        if input_method == '1':
            return get_resource_links_one_by_one()
        else:
            return get_resource_links_semicolon()

def get_resource_links_one_by_one():
    """Get multiple resource links from user one by one"""
    links = []
    while True:
        url = input("Enter URL (or 'done' to finish): ").strip()
        
        if url.lower() == 'done':
            if not links:
                print("Please enter at least one URL before finishing.")
                continue
            break
            
        if not validate_url(url):
            print("Invalid URL format. Please enter a valid URL.")
            continue
            
        links.append(url)
    
    return links

def get_resource_links_semicolon():
    """Get multiple resource links from user separated by semicolons"""
    while True:
        urls_input = input("Paste URLs (separated by semicolons): ").strip()
        if not urls_input:
            print("Please enter at least one URL.")
            continue
            
        links = [url.strip() for url in urls_input.split(';')]
        valid_links = []
        invalid_links = []
        
        for url in links:
            if validate_url(url):
                valid_links.append(url)
            else:
                invalid_links.append(url)
        
        if not valid_links:
            print("No valid URLs found. Please try again.")
            continue
            
        if invalid_links:
            print("\nThe following URLs were invalid and will be skipped:")
            for url in invalid_links:
                print(f"- {url}")
            print("\nProceeding with valid URLs only.")
        
        return valid_links

def get_manga_names(links):
    """Get manga names for all links"""
    print("\nEnter manga names for each URL.")
    print("==============================")
    
    names = {}
    for i, url in enumerate(links, 1):
        while True:
            name = input(f"Enter name for URL {i} ({url}): ").strip()
            if name:
                names[url] = sanitize_filename(name)
                break
            print("Name cannot be empty. Please try again.")
    
    return names

def process_resources():
    """Process multiple manga/doujin resources"""
    # Get all links first
    manga_links = get_multiple_links()
    
    # Get all manga names
    manga_names = get_manga_names(manga_links)
    
    # Get common resource type for all links
    print("\nSelect Resource Type for all entries:")
    resource_type = get_resource_type()
    
    # Process each link
    results = []
    for i, manga_url in enumerate(manga_links, 1):
        print(f"\nProcessing resource {i}/{len(manga_links)}")
        print("==============================")
        print(f"URL: {manga_url}")
        print(f"Name: {manga_names[manga_url]}")
        
        # Process the resource
        success = process_single_resource(manga_url, manga_names[manga_url], resource_type)
        results.append({
            "url": manga_url,
            "name": manga_names[manga_url],
            "success": success
        })
    
    # Print summary
    print("\nProcessing Summary:")
    print("==============================")
    for result in results:
        status = "✓ Success" if result["success"] else "✗ Failed"
        print(f"{status}: {result['name']} ({result['url']})")
    
    return all(r["success"] for r in results)

def process_single_resource(manga_url, manga_name, resource_type, base_name=None, starting_chapter=None, metadata=None, current_index=None):
    """Process a single manga/doujin resource"""
    # Set up paths
    project_path = os.path.dirname(os.path.abspath(__file__))
    temp_folder = os.path.join(project_path, "temp_download")
    
    # Set final export path based on resource type and whether it's part of a multiple link batch
    export_base = "G:\\My Drive\\Komga Src"
    if base_name:
        # For multiple links, use the base_name as the folder name
        if resource_type == "Manga":
            export_path = os.path.join(export_base, "Manga", base_name)
        else:  # Doujin/One-shot
            export_path = os.path.join(export_base, "Doujins", base_name)
    else:
        # For single links, use the original structure
        if resource_type == "Manga":
            export_path = os.path.join(export_base, "Manga", manga_name)
        else:  # Doujin/One-shot
            export_path = os.path.join(export_base, "Doujins", manga_name)
    
    # Download manga
    print(f"\nDownloading manga to temporary folder...")
    if not download_manga(manga_url, temp_folder):
        print("Failed to download manga.")
        return False
    
    # Find all chapter folders in the nested structure
    print("Finding chapter folders...")
    chapter_folders = find_chapter_folders(temp_folder)
    
    if not chapter_folders:
        print("No chapter folders found with images.")
        return False
    
    # Sort folders to ensure consistent ordering
    chapter_folders.sort()
    
    # First rename all chapter folders
    print("Renaming chapter folders...")
    renamed_folders = []
    chapter_counter = 1
    
    for folder in chapter_folders:
        if resource_type == "Doujin":
            # For doujins/one-shots, just use the manga name
            new_name = manga_name
            new_path = folder.parent / new_name
            try:
                folder.rename(new_path)
                renamed_folders.append(new_path)
            except FileExistsError:
                # If folder already exists, append a number
                counter = 1
                while True:
                    new_name = f"{manga_name}_{counter}"
                    new_path = folder.parent / new_name
                    if not new_path.exists():
                        folder.rename(new_path)
                        renamed_folders.append(new_path)
                        break
                    counter += 1
        else:
            # For regular manga, try to extract chapter info
            volume, chapter, chapter_name = extract_chapter_info(folder.name)
            
            if chapter is not None:
                # Build the new name with extracted info
                new_name_parts = []
                if volume:
                    new_name_parts.append(f"Volume {volume}")
                new_name_parts.append(f"Chapter {chapter}")
                if chapter_name:
                    new_name_parts.append(chapter_name)
                
                new_name = " - ".join(new_name_parts)
            else:
                # If we can't extract chapter info, use sequential numbering
                new_name = f"Chapter {chapter_counter}"
                chapter_counter += 1
            
            new_path = folder.parent / new_name
            
            try:
                folder.rename(new_path)
                renamed_folders.append(new_path)
            except FileExistsError:
                # If folder already exists, append a number
                counter = 1
                while True:
                    new_name = f"Chapter {chapter_counter}_{counter}"
                    new_path = folder.parent / new_name
                    if not new_path.exists():
                        folder.rename(new_path)
                        renamed_folders.append(new_path)
                        break
                    counter += 1
    
    # Convert to CBZ
    print("Converting to CBZ format...")
    os.makedirs(export_path, exist_ok=True)
    
    # Process each renamed chapter folder
    for i, folder in enumerate(renamed_folders):
        if base_name:
            # For multiple links, use the base_name and chapter number starting from user's input
            chapter_number = starting_chapter + current_index if starting_chapter is not None else current_index + 1
            convert_folder_to_cbz(folder, export_path, base_name, chapter_number)
        else:
            # For single links, use the original naming
            convert_folder_to_cbz(folder, export_path)
    
    # Save metadata including the URL
    print("Saving metadata...")
    is_multiple = base_name is not None
    save_metadata(export_path, manga_name, manga_url, is_multiple, metadata)
    
    # Clean up temp folder
    print("Cleaning up temporary files...")
    shutil.rmtree(temp_folder)
    
    print(f"\nProcess completed successfully!")
    print(f"CBZ files have been saved to: {export_path}")
    return True

def get_single_or_multiple():
    """Ask user whether they want to input single or multiple links"""
    print("\nSelect Input Type:")
    print("1. Single Link")
    print("2. Multiple Links")
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            return choice == '1'
        print("Invalid choice. Please enter 1 or 2.")

def get_base_name():
    """Get the base name for multiple resources"""
    return get_valid_input("Enter the base name for the resources: ", validate_manga_name)

def get_starting_chapter():
    """Get the starting chapter number for multiple resources"""
    while True:
        try:
            chapter = int(input("Enter the starting chapter number: "))
            if chapter > 0:
                return chapter
            print("Chapter number must be positive.")
        except ValueError:
            print("Please enter a valid number.")

def main():
    while True:
        # Step 1: Ask for resource type
        print("\nWhat type of resource is this?")
        resource_type = get_resource_type()
        
        # Step 2: Ask for single or multiple links
        is_single = get_single_or_multiple()
        
        # Step 3: Get links
        if is_single:
            manga_url = get_single_link()
            manga_name = get_valid_input(f"Enter the name of the {resource_type.lower()}: ", validate_manga_name)
            manga_links = [manga_url]
            manga_names = {manga_url: manga_name}
            base_name = None
            starting_chapter = None
            metadata = None
        else:
            manga_links = get_multiple_links()
            base_name = get_base_name()
            starting_chapter = get_starting_chapter()
            manga_names = {}
            for i, url in enumerate(manga_links):
                manga_names[url] = f"{base_name} Chapter {starting_chapter + i}"
            metadata = {
                "resources": [],
                "last_updated": datetime.datetime.now().isoformat()
            }
        
        # Step 5: Process resources
        results = []
        for i, manga_url in enumerate(manga_links, 1):
            print(f"\nProcessing resource {i}/{len(manga_links)}")
            print("==============================")
            print(f"URL: {manga_url}")
            print(f"Name: {manga_names[manga_url]}")
            
            success = process_single_resource(manga_url, manga_names[manga_url], resource_type, base_name, starting_chapter, metadata, i-1)
            results.append({
                "url": manga_url,
                "name": manga_names[manga_url],
                "success": success
            })
        
        # Step 6: Print summary
        print("\nProcessing Summary:")
        print("==============================")
        for result in results:
            status = "✓ Success" if result["success"] else "✗ Failed"
            print(f"{status}: {result['name']} ({result['url']})")
        
        # Step 7: Ask if user wants to add more resources
        print("\nWould you like to process more resources?")
        choice = input("Enter 'y' to continue or any other key to exit: ").strip().lower()
        if choice != 'y':
            print("Exiting program. Goodbye!")
            break

if __name__ == "__main__":
    main()
