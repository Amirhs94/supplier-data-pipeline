#!/usr/bin/env python3
"""
load_to_db.py
Creates SQLite DB and loads product metadata and cleaned supplier data.

Usage:
  python src/load_to_db.py --meta data/product_metadata.csv --cleaned data/cleaned_supplier.csv --db parts_avatar.db
"""
import argparse, sqlite3, pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True)
    ap.add_argument("--cleaned", required=True)
    ap.add_argument("--db", required=True)
    args = ap.parse_args()

    meta = pd.read_csv(args.meta)
    cleaned = pd.read_csv(args.cleaned, parse_dates=["entry_date_clean"])

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_metadata (
            product_id TEXT PRIMARY KEY,
            supplier_part_id TEXT,
            category TEXT,
            product_name TEXT
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_product_metadata_supplier_part_id ON product_metadata(supplier_part_id);")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS supplier_clean (
            supplier_part_id TEXT,
            product_id TEXT,
            category TEXT,
            product_name TEXT,
            stock_level_clean REAL,
            cost_price_clean REAL,
            entry_date_clean TEXT,
            stock_imputed_flag INTEGER,
            cost_price_imputed_flag INTEGER,
            stock_level_raw TEXT,
            cost_price_raw TEXT,
            entry_date_raw TEXT,
            PRIMARY KEY (supplier_part_id, entry_date_clean)
        );
    """)

    # load product metadata
    for c in ["supplier_part_id","product_id","category","product_name"]:
        if c not in meta.columns: meta[c]=None
    meta_rows=meta[["product_id","supplier_part_id","category","product_name"]]
    meta_rows.to_sql("product_metadata", conn, if_exists="replace", index=False)

    # load supplier_clean
    for c in ["stock_level","cost_price","entry_date"]:
        if c not in cleaned.columns: cleaned[c]=None
    cleaned_sql=cleaned.rename(columns={
        "stock_level":"stock_level_raw",
        "cost_price":"cost_price_raw",
        "entry_date":"entry_date_raw"
    })
    insert_cols=["supplier_part_id","product_id","category","product_name",
                 "stock_level_clean","cost_price_clean","entry_date_clean",
                 "stock_imputed_flag","cost_price_imputed_flag",
                 "stock_level_raw","cost_price_raw","entry_date_raw"]
    for c in insert_cols:
        if c not in cleaned_sql.columns: cleaned_sql[c]=None

    cleaned_sql[insert_cols].to_sql("supplier_clean", conn, if_exists="replace", index=False)

    conn.commit(); conn.close()
    print("Loaded tables: product_metadata, supplier_clean")

if __name__=="__main__":
    main()
