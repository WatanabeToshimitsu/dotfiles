"""Shorten the still stretches of a screen recording.

Usage: python3 -I trim_idle.py IN.mp4 OUT.mp4 [--hold 1.2] [--lead 0.5] [--tail 1.5]

Every still stretch keeps its first HOLD seconds (the new state stays readable);
the opening stillness keeps its last LEAD seconds, the closing one TAIL seconds.
"""

import argparse
import re
import subprocess

NOISE = "0.00005"  # small enough that a moving pointer counts as motion
MIN_STILL = "0.4"


def duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out)


def stills(path: str, total: float) -> list[tuple[float, float]]:
    log = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-vf", f"freezedetect=n={NOISE}:d={MIN_STILL}",
         "-map", "0:v", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    ).stderr
    starts = [float(v) for v in re.findall(r"freeze_start: ([0-9.]+)", log)]
    ends = [float(v) for v in re.findall(r"freeze_end: ([0-9.]+)", log)]
    ends += [total] * (len(starts) - len(ends))
    merged: list[tuple[float, float]] = []
    for start, end in zip(starts, ends):
        # A one-frame flicker splits one still into two; treat them as one.
        if merged and start - merged[-1][1] < 0.2:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def keep_ranges(total: float, still: list[tuple[float, float]], hold: float, lead: float, tail: float):
    cuts = []
    for start, end in still:
        if start <= 0.3:
            cut = (start, max(start, end - lead))
        elif end >= total - 0.05:
            cut = (start + tail, end)
        else:
            cut = (start + hold, end)
        if cut[1] - cut[0] > 0.05:
            cuts.append(cut)
    keep, cursor = [], 0.0
    for start, end in cuts:
        if start > cursor:
            keep.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < total:
        keep.append((cursor, total))
    return keep


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("dst")
    parser.add_argument("--hold", type=float, default=1.2)
    parser.add_argument("--lead", type=float, default=0.5)
    parser.add_argument("--tail", type=float, default=1.5)
    args = parser.parse_args()

    total = duration(args.src)
    keep = keep_ranges(total, stills(args.src, total), args.hold, args.lead, args.tail)
    expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in keep)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", args.src, "-vf",
         f"select='{expr}',setpts=N/FRAME_RATE/TB", "-an", "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", args.dst],
        check=True,
    )
    print(f"{total:.1f}s -> {duration(args.dst):.1f}s, kept {len(keep)} ranges")


if __name__ == "__main__":
    main()
