# This script renames all 'HTML.txt' files in nonHTMLDatasets/german_dataset subfolders to 'HTML.html'.
import os

def rename_and_move_html_txt(base_dir, target_dir):
	for root, dirs, files in os.walk(base_dir):
		for file in files:
			if file == 'HTML.txt':
				old_path = os.path.join(root, file)
				# Rename to HTML.html in the same folder first
				temp_html_path = os.path.join(root, 'HTML.html')
				os.rename(old_path, temp_html_path)
				# Determine subfolder name (e.g., '65', '29', etc.)
				subfolder = os.path.basename(root)
				# Ensure target directory exists
				os.makedirs(target_dir, exist_ok=True)
				# Move to /dataSets/german_dataset with subfolder name
				target_path = os.path.join(target_dir, f'{subfolder}_HTML.html')
				os.replace(temp_html_path, target_path)
				print(f"Moved: {temp_html_path} -> {target_path}")

if __name__ == "__main__":
	base_dir = os.path.join(os.path.dirname(__file__), 'nonHTMLDatasets', 'german_dataset')
	target_dir = os.path.join(os.path.dirname(__file__), 'dataSets', 'german_dataset')
	rename_and_move_html_txt(base_dir, target_dir)
