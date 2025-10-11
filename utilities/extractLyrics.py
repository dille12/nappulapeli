import os
import json

def extract_subs(json_data):
    result = []
    for ev in json_data.get("events", []):
        start = ev.get("tStartMs")
        segs = ev.get("segs")
        if start is None or segs is None:
            continue
        for seg in segs:
            word = seg.get("utf8", "").strip()
            if not word:
                continue
            offset = seg.get("tOffsetMs", 0)
            timestamp = (start + offset) / 1000.0
            result.append([timestamp, word])
    return result


def get_subs_for_track(track_path):
    base, _ = os.path.splitext(track_path)
    json_path = base + ".fi.json3"
    print(json_path)
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return extract_subs(data)
    return None


if __name__ == "__main__":
    import json
    import sys

    input_file = "tracktest/PETRI NYGÅRD： SELVÄ PÄIVÄ feat. LORD EST [OqoKizBhmyA].fi.json3"

    subtitles = get_subs_for_track(input_file)
    for start, text in subtitles:
        print(f"{start:.3f} {text}")