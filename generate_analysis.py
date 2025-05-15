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

        # message size
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

        # collect all stat dicts under a prefix
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

        # flatten into base row
        for prefix, stats in stat_dicts.items():
            for stat_name, value in stats.items():
                base[f"{prefix}_{stat_name}"] = value

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

    for key, label in metrics_labels.items():
        for perc in percentiles:
            # determine the full column name
            suffix = "_hz" if "rate" in key else "_ms"
            col = f"{key}_{perc}{suffix}"
            if col not in df.columns:
                continue

            plt.figure()
            for middleware in df["middleware"].dropna().unique():
                sub = df[df["middleware"] == middleware].sort_values("num_bytes")
                # convert bytes → KiB
                x_kib = sub["num_bytes"] / 1024.0
                plt.scatter(
                    x_kib,
                    sub[col],
                    marker="o",
                    label=middleware,
                )

            plt.xlabel("Message Size (KiB)")
            plt.ylabel(label)
            plt.title(f"{label} ({perc}) vs. Message Size")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(output_dir / f"{key}_{perc}_vs_msg_size.png")
            if show:
                plt.show()
            plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate LCM/eCAL benchmark reports and plot p50/p90 stats"
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing YAML benchmark reports",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Directory to write aggregated CSV and plots",
    )
    parser.add_argument("--show", action="store_true", default=False)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    df = load_reports(args.input_dir)
    if df.empty:
        print(f"No valid reports found in {args.input_dir}")
        return

    # 1) Write aggregated CSV
    csv_file = args.output_dir / "aggregated.csv"
    df.to_csv(csv_file, index=False)
    print(f"Saved aggregated data to {csv_file}")

    # 2) Plot separate p50 & p90 plots for each metric
    plot_percentiles(df, args.output_dir, show=args.show)
    print(f"Plots saved to {args.output_dir}")


if __name__ == "__main__":
    main()
