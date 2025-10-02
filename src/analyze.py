#!/usr/bin/env python3
"""
analyze.py

Queries parts_avatar.db and produces CSV & chart outputs:

1) Average cost price per product category
2) Top 5 parts with the highest stock levels (latest snapshot per part)
3) Monthly trend of *new* parts (counts each supplier_part_id only in its first month)

Usage (from repo root):
  python src/analyze.py --db parts_avatar.db --outdir outputs/
"""

import argparse
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def chart_avg_cost_by_category(df: pd.DataFrame, outpath: Path) -> None:
    plt.figure()
    df_sorted = df.sort_values("avg_cost_price", ascending=False)
    plt.bar(df_sorted["category"].astype(str), df_sorted["avg_cost_price"])
    plt.title("Average Cost Price per Category")
    plt.xlabel("Category")
    plt.ylabel("Average Cost Price")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()


def chart_new_parts_over_time(df: pd.DataFrame, outpath: Path) -> None:
    plt.figure()
    plt.plot(df["month"], df["new_parts"], marker="o")
    plt.title("New Parts Entries Over Time (Monthly)")
    plt.xlabel("Month")
    plt.ylabel("New Parts")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()


def main():
    # ---------------------------
    # CLI arguments
    # ---------------------------
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Path to SQLite DB (e.g., parts_avatar.db)")
    ap.add_argument("--outdir", required=True, help="Directory for CSVs and charts")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # ---------------------------
    # Connect to the DB
    # ---------------------------
    conn = sqlite3.connect(args.db)

    # ---------------------------
    # 1) Average cost price per category
    # ---------------------------
    q1 = """
    SELECT
      COALESCE(category, 'Uncategorized') AS category,
      AVG(cost_price_clean) AS avg_cost_price,
      COUNT(*) AS n_parts
    FROM supplier_clean
    GROUP BY category
    ORDER BY avg_cost_price DESC;
    """
    df_cost = pd.read_sql_query(q1, conn)
    df_cost.to_csv(outdir / "avg_cost_price_per_category.csv", index=False)
    chart_avg_cost_by_category(df_cost, outdir / "avg_cost_price_per_category.png")

    # ---------------------------
    # 2) Top-5 parts by stock (latest snapshot per part)
    # ---------------------------
    q2 = """
    WITH latest AS (
      SELECT supplier_part_id, MAX(entry_date_clean) AS max_date
      FROM supplier_clean
      GROUP BY supplier_part_id
    )
    SELECT
      sc.supplier_part_id,
      sc.product_name,
      sc.category,
      sc.stock_level_clean,
      sc.cost_price_clean,
      sc.entry_date_clean
    FROM supplier_clean sc
    JOIN latest l
      ON sc.supplier_part_id = l.supplier_part_id
     AND sc.entry_date_clean = l.max_date
    ORDER BY sc.stock_level_clean DESC
    LIMIT 5;
    """
    df_top5 = pd.read_sql_query(q2, conn)
    df_top5.to_csv(outdir / "top5_stock_levels.csv", index=False)

    # 3) Monthly trend of all parts entries (count ALL rows per month)
    q3 = """
      SELECT
      strftime('%Y-%m-01', replace(entry_date_clean,'T',' ')) AS month,
    COUNT(*) AS new_parts
    FROM supplier_clean
    WHERE entry_date_clean IS NOT NULL
    GROUP BY month
    ORDER BY month;
    """

    df_new = pd.read_sql_query(q3, conn)
    df_new.to_csv(outdir / "new_parts_over_time_monthly.csv", index=False)
    if len(df_new) > 0:
        chart_new_parts_over_time(df_new, outdir / "new_parts_over_time_monthly.png")

        # Optional: also write cumulative totals (nice for dashboards)
        df_new = df_new.sort_values("month").reset_index(drop=True)
        df_new["cumulative_parts"] = df_new["new_parts"].cumsum()
        df_new.to_csv(outdir / "new_parts_over_time_monthly_with_cumulative.csv", index=False)

    conn.close()
    print(f"Analysis outputs written to {outdir}")


if __name__ == "__main__":
    main()
