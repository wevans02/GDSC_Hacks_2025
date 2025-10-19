'''
Basically, how I manage the documents I scrape depends onhow long they are. 
This is a small script so I can get an idea of how long all my documents are. 
For the ones that are short enough, I can send everything to GPT in one prompt
If theres more, I may need to break them up into chunks.

Arguments:
--root crawl_out/markdown           # the folder location of scraped markdown
--pattern "*.md"                    # Regex pattern to match to know what files to check
--csv crawl_out/corpus_stats.csv    # output for stats csv
--charts-dir crawl_out/charts       # output for histogram png
--model gpt-4o-mini                 # model tokenizer to use to count tokens

Outputs:
hist_tokens_model.png / hist_words.png      histogram of lengths by words and tokens
corpus_stats.csv                            summary table of lengths
'''

import argparse
import csv
import os
from pathlib import Path
import re
from typing import Optional, Tuple, List, Dict
import statistics


# import tiktoken to get token count
try:
    import tiktoken
    _enc_cache = {}
    def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
        enc = _enc_cache.get(model)
        if enc is None:
            enc = tiktoken.encoding_for_model(model)
            _enc_cache[model] = enc
        return len(enc.encode(text))
    HAVE_TIKTOKEN = True
except Exception:
    HAVE_TIKTOKEN = False

# matplotlib for histograms
try:
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except Exception:
    HAVE_MPL = False

# takes in text string and outputs (bytes, chars, words, lines) length.
def simple_counts(text: str) -> Tuple[int, int, int, int]:
    b = len(text.encode("utf-8", errors="ignore"))
    c = len(text)
    # word split: collapse whitespace and split
    w = len(re.findall(r"\S+", text))
    l = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return b, c, w, l

# count tokens - either using tokenizer or heuristic
def token_estimates(text: str, model: str) -> Dict[str, int]:
    if HAVE_TIKTOKEN:
        t = count_tokens(text, model=model)
        return {"tokens_model": t, "tokens_est_char4": int(len(text) / 4), "tokens_est_w1_33": None}
    else:
        # Two rough heuristics
        char4 = int(len(text) / 4)                    # ~4 chars per token
        w133 = int(len(re.findall(r"\S+", text)) * 1.33)  # ~1.33 words per token
        return {"tokens_model": None, "tokens_est_char4": char4, "tokens_est_w1_33": w133}

# go through each extracted file and count lengths, add to summary table
def scan_dir(
    root: Path,
    pattern: str,
    model: str,
    save_csv: Path
) -> List[Dict]:
    rows = []
    files = sorted(root.rglob(pattern))
    for fp in files:
        if not fp.is_file():
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            # Skip unreadable files
            continue

        b, c, w, l = simple_counts(text)
        toks = token_estimates(text, model)
        row = {
            "rel_path": str(fp.relative_to(root)),
            "abs_path": str(fp.resolve()),
            "bytes": b,
            "chars": c,
            "words": w,
            "lines": l,
            "tokens_model": toks["tokens_model"],
            "tokens_est_char4": toks["tokens_est_char4"],
            "tokens_est_w1_33": toks["tokens_est_w1_33"],
        }
        rows.append(row)

    # write CSV
    save_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rel_path","abs_path","bytes","chars","words","lines",
        "tokens_model","tokens_est_char4","tokens_est_w1_33"
    ]
    with save_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return rows

# get distribution stats on length
def pct(vs: List[int], p: float) -> int:
    if not vs: return 0
    return int(statistics.quantiles(vs, n=100, method="inclusive")[max(0, min(99, int(p)-1))])

# prints out summary - mean/median/quantiles, longest/shortest 10
def print_summary(rows: List[Dict], use_model: bool):
    if not rows:
        print("No files found.")
        return
    n = len(rows)
    words = [r["words"] for r in rows]
    chars = [r["chars"] for r in rows]
    if use_model:
        tokens = [r["tokens_model"] for r in rows if r["tokens_model"] is not None]
        token_label = "tokens_model"
    else:
        # prefer char/4 estimate
        tokens = [r["tokens_est_char4"] for r in rows]
        token_label = "tokens_est_char4"

    def stats(name, arr):
        if not arr: return f"{name}: (no data)"
        return (
            f"{name}: count={len(arr)}, "
            f"mean={int(statistics.mean(arr))}, "
            f"median={int(statistics.median(arr))}, "
            f"p90={pct(arr,90)}, p95={pct(arr,95)}, p99={pct(arr,99)}, "
            f"max={max(arr)}"
        )

    print(f"\nAnalyzed {n} files.")
    print(stats("Words", words))
    print(stats("Chars", chars))
    print(stats("Tokens" + (" (model)" if use_model else " (~char/4)"), tokens))

    # Print top 10 largest by tokens
    top = sorted(rows, key=lambda r: (r[token_label] or 0), reverse=True)[:10]
    print("\nTop 10 by tokens:")
    for r in top:
        print(f"- {r['rel_path']} | tokens={r[token_label]} | words={r['words']} | chars={r['chars']}")

    # print bottom 10:
    top = sorted(rows, key=lambda r: (r[token_label] or 0), reverse=False)[:10]
    print("\Bottom 10 by tokens:")
    for r in top:
        print(f"- {r['rel_path']} | tokens={r[token_label]} | words={r['words']} | chars={r['chars']}")

# use matplotlib to make histograms
def make_histograms(
    rows: List[Dict],
    out_dir: Path,
    use_model: bool,
    max_bins: int = 50
):
    if not HAVE_MPL or not rows:
        if not HAVE_MPL:
            print("matplotlib not installed; skipping charts.")
        return
    out_dir.mkdir(parents=True, exist_ok=True)

    words = [r["words"] for r in rows]
    if use_model:
        tokens = [r["tokens_model"] for r in rows if r["tokens_model"] is not None]
        token_label = "Tokens (tiktoken)"
        token_fname = "hist_tokens_model.png"
    else:
        tokens = [r["tokens_est_char4"] for r in rows]
        token_label = "Tokens (~chars/4)"
        token_fname = "hist_tokens_est_char4.png"

    # Words histogram
    plt.figure()
    plt.hist(words, bins=min(max_bins, max(10, int(len(words) ** 0.5))))
    plt.title("File length distribution (Words)")
    plt.xlabel("Words per file")
    plt.ylabel("Count of files")
    plt.tight_layout()
    plt.savefig(out_dir / "hist_words.png", dpi=150)
    plt.close()

    # Tokens histogram
    if tokens:
        plt.figure()
        plt.hist(tokens, bins=min(max_bins, max(10, int(len(tokens) ** 0.5))))
        plt.title(f"File length distribution ({token_label})")
        plt.xlabel("Tokens per file")
        plt.ylabel("Count of files")
        plt.tight_layout()
        plt.savefig(out_dir / token_fname, dpi=150)
        plt.close()

def main():
    p = argparse.ArgumentParser(description="Analyze corpus file sizes (words/chars/tokens) and produce CSV + histograms.")
    p.add_argument("root", type=str, help="Root directory (e.g., crawl_out/markdown)")
    p.add_argument("--pattern", type=str, default="*.md", help="Glob pattern to include (default: *.md)")
    p.add_argument("--csv", type=str, default="corpus_stats.csv", help="CSV output path")
    p.add_argument("--charts-dir", type=str, default="charts", help="Directory to save histograms PNGs")
    p.add_argument("--model", type=str, default="gpt-4o-mini", help="tiktoken model name for token counting")
    args = p.parse_args()

    root = Path(args.root)
    save_csv = Path(args.csv)
    charts_dir = Path(args.charts_dir)

    rows = scan_dir(root, args.pattern, args.model, save_csv)
    use_model = HAVE_TIKTOKEN
    print_summary(rows, use_model=use_model)
    make_histograms(rows, charts_dir, use_model=use_model)

    print(f"\nCSV saved to: {save_csv.resolve()}")
    if HAVE_MPL:
        print(f"Charts saved to: {charts_dir.resolve()}")
    else:
        print("Install matplotlib to generate charts: pip install matplotlib")

if __name__ == "__main__":
    main()
