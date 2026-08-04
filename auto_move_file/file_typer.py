import base64
import os
import sys
import time
import zlib

import pyautogui


def get_file_path():
    """Get file path from user input"""
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = input("Enter file path or directory: ").strip()
    
    return path

def read_file_content(file_path):
    """Read content from a file using os module"""
    if not os.path.exists(file_path):
        print(f"Error: Path '{file_path}' does not exist")
        return None
    
    if os.path.isdir(file_path):
        print(f"Error: '{file_path}' is a directory, not a file")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def encode_content(content):
    """Zlib-compress then base64 encode the content"""
    compressed = zlib.compress(content.encode('utf-8'), level=9)
    encoded = base64.b64encode(compressed).decode('utf-8')
    return encoded

def collect_files(path):
    """Collect a list of files from a single file or a directory (recursively)"""
    files = []
    if os.path.isdir(path):
        for root, _, filenames in os.walk(path):
            for name in filenames:
                files.append(os.path.join(root, name))
    elif os.path.isfile(path):
        files.append(path)
    return files

def build_encoded_lines(path):
    """Build lines in the format: relative\\path(base64 encoded): <data>"""
    lines = []
    # Base directory used to compute relative paths
    base = os.path.dirname(path) if os.path.isfile(path) else path
    for file_path in collect_files(path):
        content = read_file_content(file_path)
        if content is None:
            continue
        rel_path = os.path.relpath(file_path, base) if base else file_path
        encoded = encode_content(content)
        lines.append(f"{rel_path}(base64 encoded): {encoded}")
    return lines

def type_content(content):
    """Simulate typing the content using pyautogui"""
    print("Starting to type in 10 seconds... Click on the target window!")
    print("Press Ctrl+C to stop")
    for i in range(0,10, 1):
        print(f"{10 - i}...", end='', flush=True)
        time.sleep(1)
    
    try:
        # Type the content with a small delay between characters
        pyautogui.typewrite(content, interval=0.01)
        print("\nTyping complete!")
    except KeyboardInterrupt:
        print("\nTyping interrupted by user")
    except Exception as e:
        print(f"Error during typing: {e}")

def main():
    """Main function"""
    print("=" * 50)
    print("File Content Typer (Base64)")
    print("=" * 50)
    
    # Get file path
    file_path = get_file_path()
    
    if not os.path.exists(file_path):
        print(f"Error: Path '{file_path}' does not exist")
        return
    
    # Build encoded lines (works for a single file or a whole directory)
    lines = build_encoded_lines(file_path)
    if not lines:
        print("No readable files found.")
        return
    
    output = "\n".join(lines)
    
    print(f"\nEncoded {len(lines)} file(s):")
    print("-" * 50)
    print(output[:300] + "..." if len(output) > 300 else output)
    print("-" * 50)
    
    # Ask for confirmation
    confirm = input("\nType out the encoded content? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled")
        return
    
    # Type the encoded content
    type_content(output)

if __name__ == "__main__":
    main()
