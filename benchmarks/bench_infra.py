#!/usr/bin/env python3
"""Infra benchmark for the FarmHouse Ollama pool.

Phases:
  1. warm single-stream throughput (3 runs)
  2. concurrency scaling: 1, 2, 4, 8 parallel streams
  3. context-size probe: 2k, 8k, 16k token prompts
  4. cold start (unloads model — runs last)

Usage: python3 bench_infra.py [--host http://172.19.96.1:11434] [--model qwen3.5:9b]
"""
import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

GEN_PROMPT = "Write a detailed explanation of how a hash table handles collisions."
NUM_PREDICT = 256


def generate(host, model, prompt, num_predict=NUM_PREDICT, keep_alive=None, timeout=600):
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"num_predict": num_predict},
    }
    if keep_alive is not None:
        body["keep_alive"] = keep_alive
    t0 = time.monotonic()
    r = requests.post(f"{host}/api/generate", json=body, timeout=timeout)
    wall = time.monotonic() - t0
    r.raise_for_status()
    d = r.json()
    return {
        "wall_s": round(wall, 2),
        "load_s": round(d.get("load_duration", 0) / 1e9, 2),
        "prompt_tokens": d.get("prompt_eval_count", 0),
        "prompt_eval_s": round(d.get("prompt_eval_duration", 0) / 1e9, 2),
        "gen_tokens": d.get("eval_count", 0),
        "gen_s": round(d.get("eval_duration", 0) / 1e9, 2),
        "tok_per_s": round(d.get("eval_count", 0) / (d.get("eval_duration", 1) / 1e9), 1),
    }


def phase_warm(host, model):
    print("== phase 1: warm single-stream ==", flush=True)
    generate(host, model, "hi", num_predict=8)  # ensure loaded
    runs = [generate(host, model, GEN_PROMPT) for _ in range(3)]
    for r in runs:
        print(f"  {r['tok_per_s']} tok/s (wall {r['wall_s']}s)", flush=True)
    return runs


def phase_concurrency(host, model):
    print("== phase 2: concurrency scaling ==", flush=True)
    out = {}
    for n in (1, 2, 4, 8):
        t0 = time.monotonic()
        with ThreadPoolExecutor(max_workers=n) as ex:
            futs = [ex.submit(generate, host, model, GEN_PROMPT + f" (variant {i})") for i in range(n)]
            runs = [f.result() for f in futs]
        wall = time.monotonic() - t0
        rates = [r["tok_per_s"] for r in runs]
        agg = round(sum(r["gen_tokens"] for r in runs) / wall, 1)
        out[n] = {"wall_s": round(wall, 2), "per_stream_tok_s": rates, "aggregate_tok_s": agg, "runs": runs}
        print(f"  n={n}: wall {wall:.1f}s, per-stream {rates}, aggregate {agg} tok/s", flush=True)
    return out


def phase_context(host, model):
    print("== phase 3: context-size probe ==", flush=True)
    # ~4 chars/token filler; question at the end forces reading the prompt
    out = {}
    for target_tokens in (2000, 8000, 16000):
        filler = ("The quick brown fox jumps over the lazy dog. " * 200)
        text = (filler * (target_tokens // 200))[: target_tokens * 4]
        prompt = text + "\n\nHow many words are in the sentence repeated above? Answer briefly."
        try:
            r = generate(host, model, prompt, num_predict=64)
            pe_rate = round(r["prompt_tokens"] / r["prompt_eval_s"], 1) if r["prompt_eval_s"] else None
            out[target_tokens] = {**r, "prompt_eval_tok_s": pe_rate}
            print(f"  ~{target_tokens} tok prompt: actual {r['prompt_tokens']} tok, "
                  f"prompt-eval {r['prompt_eval_s']}s ({pe_rate} tok/s), wall {r['wall_s']}s", flush=True)
        except Exception as e:
            out[target_tokens] = {"error": str(e)}
            print(f"  ~{target_tokens} tok prompt: FAILED {e}", flush=True)
    return out


def phase_cold(host, model):
    print("== phase 4: cold start ==", flush=True)
    requests.post(f"{host}/api/generate", json={"model": model, "keep_alive": 0}, timeout=60)
    time.sleep(5)
    r = generate(host, model, "hi", num_predict=8)
    print(f"  load {r['load_s']}s, total wall {r['wall_s']}s", flush=True)
    # reload warm for whoever uses the pool next
    generate(host, model, "hi", num_predict=8)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://172.19.96.1:11434")
    ap.add_argument("--model", default="qwen3.5:9b")
    args = ap.parse_args()

    results = {"host": args.host, "model": args.model}
    results["warm"] = phase_warm(args.host, args.model)
    results["concurrency"] = phase_concurrency(args.host, args.model)
    results["context"] = phase_context(args.host, args.model)
    results["cold"] = phase_cold(args.host, args.model)

    warm_rates = [r["tok_per_s"] for r in results["warm"]]
    results["summary"] = {
        "warm_tok_s_median": statistics.median(warm_rates),
        "cold_load_s": results["cold"]["load_s"],
        "aggregate_tok_s_at_4": results["concurrency"][4]["aggregate_tok_s"],
        "scaling_4_vs_1": round(
            results["concurrency"][4]["aggregate_tok_s"] / results["concurrency"][1]["aggregate_tok_s"], 2
        ),
    }
    out = Path(__file__).parent / "results" / "infra.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nsummary: {json.dumps(results['summary'], indent=2)}")
    print(f"written: {out}")


if __name__ == "__main__":
    sys.exit(main())
