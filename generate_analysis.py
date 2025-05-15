#!/usr/bin/env python3
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml


def load_reports(input_dir: Path) -> pd.DataFrame:
    rows = []
    for filepath in input_dir.glob("*.yaml"):
        report = yaml.safe_load(filepath.read_text())
        params = report.get("parameters", {})

        # determine message size (bytes)
        msg_size = params.get("num_bytes") or report.get(
            "num_bytes_statistics", {}
        ).get("mean_bytes")
        if msg_size is None:
            continue

        base = {
            "middleware": params.get("middleware"),
            "num_msgs": params.get("num_msgs"),
            "num_bytes": msg_size,
        }

        # all the statistics dicts we care about
        stat_dicts = {
            "actual_transmission_rate_statistics": report.get(
                "actual_transmission_rate_statistics", {}
            ),
            "publish_duration_statistics": report.get(
                "publish_duration_statistics", {}
            ),
            "serialization_duration_statistics": report.get(
                "serialization_duration_statistics", {}
            ),
            "processing_rate_statistics": report.get("processing_rate_statistics", {}),
            "handle_duration_statistics": report.get("handle_duration_statistics", {}),
            "decode_duration_statistics": report.get("decode_duration_statistics", {}),
            "oneway_latency_statistics": report.get("oneway_latency_statistics", {}),
        }

        # flatten them, renaming any stddev_* → std_*
        for prefix, stats in stat_dicts.items():
            for stat_name, value in stats.items():
                # normalize stddev → std
                norm = stat_name.replace("stddev", "std")
                col = f"{prefix}_{norm}"
                base[col] = value

        rows.append(base)

    return pd.DataFrame(rows)


def plot_percentiles(df: pd.DataFrame, output_dir: Path, show: bool):
    metrics_labels = {
        "actual_transmission_rate_statistics": "Publisher Rate (Hz)",
        "processing_rate_statistics": "Subscriber Response Rate (Hz)",
        "publish_duration_statistics": "Publish Duration (ms)",
        "serialization_duration_statistics": "Serialization Duration (ms)",
        "handle_duration_statistics": "Handle Duration (ms)",
        "decode_duration_statistics": "Decode Duration (ms)",
        "oneway_latency_statistics": "One-way Latency (ms)",
    }
    percentiles = ["p50", "p90"]

    # discrete x-axis: sorted unique sizes in KiB
    sizes_kib = sorted(df["num_bytes"].unique() / 1024.0)
    mw_list = df["middleware"].dropna().unique()
    n_mw = len(mw_list)
    width = 0.8 / n_mw

    for key, label in metrics_labels.items():
        for perc in percentiles:
            suffix = "_hz" if "rate" in key else "_ms"
            col = f"{key}_{perc}{suffix}"
            if col not in df:
                continue

            plt.figure()
            for i, mw in enumerate(mw_list):
                vals = []
                for s in sizes_kib:
                    sub = df[
                        (df["middleware"] == mw) & ((df["num_bytes"] / 1024.0) == s)
                    ]
                    vals.append(sub[col].mean() if not sub.empty else 0.0)

                x = [j + i * width for j in range(len(sizes_kib))]
                plt.bar(x, vals, width=width, label=mw)

            centers = [j + width * (n_mw - 1) / 2 for j in range(len(sizes_kib))]
            plt.xticks(centers, [f"{s:.1f}" for s in sizes_kib])
            plt.xlabel("Message Size (KiB)")
            plt.ylabel(label)
            plt.title(f"{label} ({perc}) vs. Message Size")
            plt.grid(axis="y", linestyle="--", alpha=0.5)
            plt.legend()
            plt.tight_layout()
            plt.savefig(output_dir / f"{key}_{perc}_vs_msg_size.png")
            if show:
                plt.show()
            plt.close()


def plot_mean_std(df: pd.DataFrame, output_dir: Path, show: bool):
    metrics_labels = {
        "actual_transmission_rate_statistics": "Publisher Rate (Hz)",
        "processing_rate_statistics": "Subscriber Response Rate (Hz)",
        "publish_duration_statistics": "Publish Duration (ms)",
        "serialization_duration_statistics": "Serialization Duration (ms)",
        "handle_duration_statistics": "Handle Duration (ms)",
        "decode_duration_statistics": "Decode Duration (ms)",
        "oneway_latency_statistics": "One-way Latency (ms)",
    }

    sizes_kib = sorted(df["num_bytes"].unique() / 1024.0)
    mw_list = df["middleware"].dropna().unique()
    n_mw = len(mw_list)
    width = 0.8 / n_mw

    for key, label in metrics_labels.items():
        suffix = "_hz" if "rate" in key else "_ms"
        mean_col = f"{key}_mean{suffix}"
        std_col = f"{key}_std{suffix}"
        if mean_col not in df or std_col not in df:
            continue

        plt.figure()
        for i, mw in enumerate(mw_list):
            means, stds = [], []
            for s in sizes_kib:
                sub = df[(df["middleware"] == mw) & ((df["num_bytes"] / 1024.0) == s)]
                if not sub.empty:
                    means.append(sub[mean_col].mean())
                    stds.append(sub[std_col].mean())
                else:
                    means.append(0.0)
                    stds.append(0.0)

            x = [j + i * width for j in range(len(sizes_kib))]
            plt.bar(x, means, width=width, yerr=stds, capsize=4, label=mw)

        centers = [j + width * (n_mw - 1) / 2 for j in range(len(sizes_kib))]
        plt.xticks(centers, [f"{s:.1f}" for s in sizes_kib])
        plt.xlabel("Message Size (KiB)")
        plt.ylabel(label)
        plt.title(f"{label} Mean ± STD vs. Message Size")
        plt.grid(axis="y", linestyle="--", alpha=0.5)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / f"{key}_mean_std_vs_msg_size.png")
        if show:
            plt.show()
        plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate LCM/eCAL benchmark reports and plot stats"
    )
    parser.add_argument("input_dir", type=Path, help="YAML reports directory")
    parser.add_argument("output_dir", type=Path, help="Where to write CSV + plots")
    parser.add_argument(
        "--show", action="store_true", help="Display plots interactively"
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    df = load_reports(args.input_dir)
    if df.empty:
        print(f"No valid reports found in {args.input_dir}")
        return

    # ─── collapse duplicate runs by middleware & message size ───
    df = df.groupby(["middleware", "num_bytes"], as_index=False).mean()

    # 1) write out aggregated CSV
    csv_file = args.output_dir / "aggregated.csv"
    df.to_csv(csv_file, index=False)
    print(f"Saved aggregated data to {csv_file}")

    # 2) percentiles
    plot_percentiles(df, args.output_dir, show=args.show)
    # 3) mean ± std
    plot_mean_std(df, args.output_dir, show=args.show)

    print(f"All plots saved to {args.output_dir}")


if __name__ == "__main__":
    main()
