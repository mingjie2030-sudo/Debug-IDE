import os, sys, glob, subprocess

FOLDER     = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR  = os.path.join(FOLDER, "icons")
OUTPUT_DIR = os.path.join(FOLDER, "IDE-Exe")

# Force working directory to script location
os.chdir(FOLDER)
print(f"📂 Working directory: {os.getcwd()}")

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

def convert_icon(name):
    from PIL import Image
    png = os.path.join(ICONS_DIR, f"{name}.png")
    ico = os.path.join(ICONS_DIR, f"{name}.ico")
    if not os.path.exists(png):
        print(f"  ⚠️  No icon for {name}, skipping")
        return None
    Image.open(png).convert("RGBA").save(ico, format="ICO",
        sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])
    print(f"  🖼️  {name}.ico ready")
    return ico

def build(py_file):
    name = os.path.splitext(os.path.basename(py_file))[0]
    print(f"\n{'='*45}\n  Building: {name}\n{'='*45}")
    ico = convert_icon(name)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--windowed",
        "--onefile",
        f"--name={name}",
        f"--distpath={OUTPUT_DIR}",
        f"--workpath={os.path.join(FOLDER, 'build_tmp')}",
        f"--specpath={os.path.join(FOLDER, 'build_tmp')}",
        "--clean", "--noconfirm",
    ]
    if ico:
        cmd.append(f"--icon={ico}")
    cmd.append(py_file)

    ok = subprocess.run(cmd, cwd=FOLDER).returncode == 0
    print(f"  {'✅ Done' if ok else '❌ Failed'}: {name}.exe")
    return ok

def main():
    try:
        from PIL import Image
    except:
        print("Installing Pillow..."); install("pillow")
    try:
        import PyInstaller
    except:
        print("Installing PyInstaller..."); install("pyinstaller")

    os.makedirs(ICONS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    py_files = sorted([
        f for f in glob.glob(os.path.join(FOLDER, "*.py"))
        if os.path.basename(f) != "build_all.py"
    ])

    print(f"\nFound {len(py_files)} files to build:")
    for f in py_files:
        print(f"  • {os.path.basename(f)}")

    results = {}
    for f in py_files:
        results[os.path.basename(f)] = "✅" if build(f) else "❌"

    print(f"\n{'='*45}")
    print("  SUMMARY")
    print(f"{'='*45}")
    for name, status in results.items():
        print(f"  {status}  {name}")
    print(f"\n📁 Output → {OUTPUT_DIR}")
    input("\nPress Enter to close...")

if __name__ == "__main__":
    main()