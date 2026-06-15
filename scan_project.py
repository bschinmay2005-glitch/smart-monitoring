import os
import ast

def get_project_imports(target_directory="."):
    """Scans all .py files in the target directory and extracts top-level imported libraries."""
    detected_modules = set()
    
    # Walk through all files and folders in your project
    for root, _, files in os.walk(target_directory):
        for file in files:
            if file.endswith(".py") and file != os.path.basename(__file__):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=file_path)
                    
                    # Look through the structure of the Python file for imports
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                # Get the base module name (e.g., 'pandas' from 'pandas.DataFrame')
                                base_module = alias.name.split('.')[0]
                                detected_modules.add(base_module)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                base_module = node.module.split('.')[0]
                                detected_modules.add(base_module)
                except Exception as e:
                    # Ignore files that fail to parse (e.g., syntax errors or blank files)
                    continue
                    
    return sorted(list(detected_modules))

def display_imports(imports):
    print("\n==== Libraries Detected Directly in Your Project ====")
    if not imports:
        print("(No Python files or import statements found in this folder.)")
    else:
        for idx, lib in enumerate(imports, 1):
            # Differentiate built-in packages from external ones if needed
            print(f"{idx}. {lib}")
    print("=====================================================")

def main():
    # Target directory is "." which means "this current folder and everything inside it"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    while True:
        print("\n===== Project Library Manager =====")
        print("1. Scan Project & Display Active Imports")
        print("2. Exit")
        
        choice = input("Choose an option (1-2): ").strip()
        
        if choice == "1":
            # Scan the directory where the script is located
            imports = get_project_imports(current_dir)
            display_imports(imports)
        elif choice == "2":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, please select 1 or 2.")

if __name__ == "__main__":
    main()