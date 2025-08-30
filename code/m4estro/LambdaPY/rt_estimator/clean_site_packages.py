import os
import site
import shutil
from pathlib import Path

def remove_dirs_by_name(base_path: Path, dirnames: list[str]):
    for root, dirs, _ in os.walk(base_path, topdown=False):
        for d in dirs:
            if any(d.lower() == name.lower() for name in dirnames):
                shutil.rmtree(Path(root) / d, ignore_errors=True)

def remove_dirs_by_pattern(base_path: Path, patterns: list[str]):
    for d in base_path.rglob("*"):
        if d.is_dir() and any(p in d.name.lower() for p in patterns):
            shutil.rmtree(d, ignore_errors=True)

def remove_files_by_extension(base_path: Path, extensions: list[str]):
    for f in base_path.rglob("*"):
        if f.is_file() and any(f.name.lower().endswith(ext) for ext in extensions):
            try:
                f.unlink()
            except Exception:
                pass

def remove_files_by_prefix(base_path: Path, prefixes: list[str]):
    for f in base_path.rglob("*"):
        if f.is_file() and any(f.name.lower().startswith(prefix) for prefix in prefixes):
            try:
                f.unlink()
            except Exception:
                pass

def remove_files_by_pattern(base_path: Path, patterns: list[str]):
    for f in base_path.rglob("*"):
        if f.is_file() and any(p in f.name.lower() for p in patterns):
            try:
                f.unlink()
            except Exception:
                pass

def main():
    base_path = Path(site.getsitepackages()[0])
    print(f"📦 Cleaning: {base_path}")

    def get_size_and_count(p: Path):
        total_size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        total_files = sum(1 for f in p.rglob("*") if f.is_file())
        return total_size, total_files

    initial_size, initial_files = get_size_and_count(base_path)

    # Standard cleanup
    remove_dirs_by_name(base_path, [
        "tests", "test", "__pycache__",
    ])
    remove_files_by_extension(base_path, [
        ".pyc", ".pyo", ".pyd", ".md",
    ])
    remove_files_by_prefix(base_path, [
        "license", "copying", "changelog", "authors", "contributors"
    ])
    remove_dirs_by_pattern(base_path, ["dist-info", "egg-info"])

    '''
    # NVIDIA-specific cleanup
    remove_dirs_by_pattern(base_path, ["nvidia", "cuda", "cudnn", "cuml", "cupy"])
    remove_files_by_pattern(base_path, ["nvidia", "cuda", "cudnn", "cuml", "cupy"])

    # Strip large shared libraries with nvidia/cuda
    for so_file in base_path.rglob("*.so"):
        if any(p in so_file.name.lower() for p in ["nvidia", "cuda", "cudnn"]):
            try:
                so_file.unlink()
            except Exception:
                pass
    '''

    # Report
    final_size, final_files = get_size_and_count(base_path)
    saved_mb = (initial_size - final_size) / 1024 / 1024
    percent_saved = saved_mb * 100 / (initial_size / 1024 / 1024)
    print(f"📊 BEFORE: {initial_size / 1024 / 1024:.2f}MB, {initial_files} files")
    print(f"📊 AFTER:  {final_size / 1024 / 1024:.2f}MB, {final_files} files")
    print(f"✅ SAVED: {saved_mb:.2f}MB - {percent_saved:.1f}% reduction")

if __name__ == "__main__":
    main()
