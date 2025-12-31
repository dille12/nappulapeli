from pathlib import Path

ROOT = Path("C:\\Users\\Reset\\AndroidStudioProjects\\Nappula3")
EXTENSIONS = {".py", ".c", ".cpp", ".h", ".hpp", ".java", ".js", ".ts", ".kt"}
COMMENT_PREFIXES = ("#", "//")

def count_loc(path: Path) -> int:
    total = 0
    for file in path.rglob("*"):
        if not file.is_file():
            continue
        if EXTENSIONS and file.suffix not in EXTENSIONS:
            continue

        try:
            for line in file.read_text(errors="ignore").splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith(COMMENT_PREFIXES):
                    continue
                total += 1
        except Exception:
            pass
    return total

if __name__ == "__main__":
    print(count_loc(ROOT))
