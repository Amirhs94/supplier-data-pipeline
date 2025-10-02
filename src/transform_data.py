#!/usr/bin/env python3
"""
transform_data.py
Reads raw supplier and metadata CSVs, cleans and standardizes, and writes cleaned files.

Usage:
  python src/transform_data.py --in-supplier data/supplier_feed.csv --in-meta data/product_metadata.csv --out data/cleaned_supplier.csv
"""
import argparse
import math, re
from datetime import datetime
import pandas as pd
import numpy as np

def parse_stock_level(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return np.nan
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    s = str(x).strip().lower()
    if s in {"", "na", "n/a", "none", "null", "unknown"}:
        return np.nan
    if s in {"low stock", "low", "limited"}: return 5.0
    if s in {"out of stock", "oos", "zero"}: return 0.0
    if s in {"in stock", "available"}:       return 10.0
    s = s.replace(",", "")
    m = re.fullmatch(r"(?i)(\d+(\.\d+)?)([kKmMbB]?)", s)
    if m:
        val = float(m.group(1))
        suf = (m.group(3) or "").lower()
        mult = {"k":1_000,"m":1_000_000,"b":1_000_000_000}.get(suf,1)
        return val*mult
    m2 = re.search(r"(-?\d+(\.\d+)?)", s)
    if m2: return float(m2.group(1))
    return np.nan

def parse_cost(x):
    if x is None or (isinstance(x,float) and math.isnan(x)): return np.nan
    s = str(x).strip()
    if s.lower() in {"","na","n/a","none","null","unknown","-"}: return np.nan
    s = re.sub(r"[^\d\.\-]", "", s)
    if s.count(".")>1:
        p = s.split(".")
        s = p[0]+"."+ "".join(p[1:])
    try: return float(s)
    except: return np.nan

def excel_serial_to_datetime(n: float):
    try: return pd.to_datetime(n, unit="D", origin="1899-12-30")
    except: return pd.NaT

def robust_parse_date(x):
    if pd.isna(x): return pd.NaT
    if isinstance(x,(pd.Timestamp,np.datetime64)): return pd.to_datetime(x)
    s = str(x).strip()
    if s=="": return pd.NaT
    if s.isdigit():
        i=int(s)
        try:
            if i>10**12: i//=10**9
            if i>10**10: return pd.to_datetime(i,unit="ms",utc=True).tz_convert(None)
            if i>=10**9:  return pd.to_datetime(i,unit="s",utc=True).tz_convert(None)
            return excel_serial_to_datetime(float(i))
        except: pass
    try:
        f=float(s)
        if f>10_000: return excel_serial_to_datetime(f)
    except: pass
    return pd.to_datetime(s, errors="coerce", dayfirst=False, infer_datetime_format=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-supplier", required=True)
    ap.add_argument("--in-meta", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    supplier = pd.read_csv(args.in_supplier)
    meta = pd.read_csv(args.in_meta)

    # normalize column names
    supplier.columns=[re.sub(r"\s+","_",c.strip().lower()) for c in supplier.columns]
    meta.columns=[re.sub(r"\s+","_",c.strip().lower()) for c in meta.columns]
    rename_map={"supplier_sku":"supplier_part_id","sku":"supplier_part_id",
                "stock":"stock_level","qty":"stock_level","quantity":"stock_level",
                "cost":"cost_price","price":"cost_price", "part_id": "supplier_part_id",
                "part id": "supplier_part_id",  
                "date":"entry_date","created_at":"entry_date","timestamp":"entry_date"}
    supplier.rename(columns={k:v for k,v in rename_map.items() if k in supplier.columns}, inplace=True)
    meta.rename(columns={k:v for k,v in rename_map.items() if k in meta.columns}, inplace=True)

    supplier["stock_level_parsed"]=supplier.get("stock_level",np.nan).apply(parse_stock_level)
    supplier["cost_price_parsed"]=supplier.get("cost_price",np.nan).apply(parse_cost)
    supplier["entry_date_parsed"]=supplier.get("entry_date",pd.NaT).apply(robust_parse_date)

    # merge metadata
    join_cols=[c for c in["supplier_part_id"] if c in supplier.columns and c in meta.columns]
    merged=supplier.merge(meta,how="left",on=join_cols) if join_cols else supplier.copy()

    # impute cost
    if "category" in merged.columns:
        med_by_cat=merged.groupby("category",dropna=False)["cost_price_parsed"].median()
        def imp_cost(r):
            if pd.notna(r["cost_price_parsed"]): return r["cost_price_parsed"]
            cat=r.get("category",np.nan)
            return med_by_cat.get(cat,np.nan)
        merged["cost_price_imputed"]=merged.apply(imp_cost,axis=1)
    else:
        merged["cost_price_imputed"]=merged["cost_price_parsed"]
    global_med_cost=merged["cost_price_parsed"].median()
    merged["cost_price_clean"]=merged["cost_price_imputed"].fillna(global_med_cost)
    merged["cost_price_imputed_flag"]=merged["cost_price_parsed"].isna().astype(int)

    # impute stock
    if "category" in merged.columns:
        med_stock_cat=merged.groupby("category",dropna=False)["stock_level_parsed"].median()
        def imp_stock(r):
            if pd.notna(r["stock_level_parsed"]): return r["stock_level_parsed"]
            cat=r.get("category",np.nan)
            return med_stock_cat.get(cat,np.nan)
        merged["stock_level_imputed"]=merged.apply(imp_stock,axis=1)
    else:
        merged["stock_level_imputed"]=merged["stock_level_parsed"]
    global_stock_med=merged["stock_level_parsed"].median()
    merged["stock_level_clean"]=merged["stock_level_imputed"].fillna(global_stock_med).fillna(0)
    merged["stock_imputed_flag"]=merged["stock_level_parsed"].isna().astype(int)

    if "supplier_part_id" not in merged.columns:
        merged["supplier_part_id"]=merged.index.astype(str)
    merged["entry_date_clean"]=pd.to_datetime(merged["entry_date_parsed"],errors="coerce")

    cols_out=["supplier_part_id"]
    for c in["product_id","category","product_name"]:
        if c in merged.columns: cols_out.append(c)
    cols_out+=["stock_level_clean","cost_price_clean","entry_date_clean","stock_imputed_flag","cost_price_imputed_flag"]
    for raw in["stock_level","cost_price","entry_date"]:
        if raw in supplier.columns: cols_out.append(raw)

    cleaned=merged[cols_out].copy()
    cleaned.sort_values(by=["entry_date_clean","supplier_part_id"], inplace=True, na_position="last")
    cleaned.to_csv(args.out,index=False)

if __name__=="__main__":
    main()
