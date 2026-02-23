# LLM Generated Driver Code 
# Authored by Codex
# Verified by datavorous on Feb 23, 2026

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def folder_size_bytes(folder: Path) -> int:
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def compress_one(src: Path, input_dir: Path, output_dir: Path):
    relative = src.relative_to(input_dir)
    dst = (output_dir / relative).with_suffix(".bin")
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["python3", "main.py", "compress", str(src), str(dst)],
        check=True,
    )

def main():
    input_dir = Path("all_json")
    output_dir = Path("compressed_json")
    output_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(input_dir.rglob("*.json"))
    max_workers = max(1, (os.cpu_count() or 1) * 2)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(lambda src: compress_one(src, input_dir, output_dir), json_files))

    input_size = folder_size_bytes(input_dir)
    output_size = folder_size_bytes(output_dir)

    print(f"all_json total size: {input_size} bytes")
    print(f"compressed_json total size: {output_size} bytes")


if __name__ == "__main__":
    main()
