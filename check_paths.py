import os
base = os.path.dirname(os.path.abspath(__file__))
t_path = os.path.join(base, 'templates')

print(f"Project Folder: {base}")
print(f"Looking for templates in: {t_path}")
print(f"Does the folder exist? {os.path.exists(t_path)}")

if os.path.exists(t_path):
    print(f"Files inside templates: {os.listdir(t_path)}")