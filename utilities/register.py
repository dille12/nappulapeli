
from pathlib import Path

def register_gun_kill(gun_name, team_kill = False, path="weapon_kills.txt"):
    p = Path(path)
    kills = {}

    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().rsplit(" ", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    kills[parts[0]] = int(parts[1])

    kills[gun_name] = kills.get(gun_name, 0) + 1

    with p.open("w", encoding="utf-8") as f:
        for k, v in sorted(kills.items(), key=lambda x: -x[1]):
            f.write(f"{k} {v}\n")