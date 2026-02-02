# -*- coding: utf-8 -*-
import os
import ast
import pandas as pd

IN_PATH = r"D:\2025_26 Spring\Replication\Q&A.xls"

base_dir = os.path.dirname(IN_PATH)
OUT_XLSX = os.path.join(base_dir, "Q&A_with_nonanswer.xlsx")
OUT_CSV  = os.path.join(base_dir, "Q&A_with_nonanswer.csv")

from ling_features import non_answers, get_regexes_df

regexes_df = get_regexes_df()

def regex_id_to_category(rid: int):
    
    try:
        return str(regexes_df.loc[rid, "category"])
    except Exception:
        pass
    
    if "regex_id" in regexes_df.columns:
        m = regexes_df.loc[regexes_df["regex_id"] == rid, "category"]
        if len(m) > 0:
            return str(m.iloc[0])
    return None

def extract_regex_id(item):
    if item is None:
        return None
    if isinstance(item, dict):
        return item.get("regex_id", None)
    if isinstance(item, str):
        try:
            d = ast.literal_eval(item.strip())
            if isinstance(d, dict):
                return d.get("regex_id", None)
        except Exception:
            return None
    return getattr(item, "regex_id", None)

def classify_answer(ans_text, types=("REFUSE", "UNABLE", "AFTERCALL")):
    if ans_text is None or (isinstance(ans_text, float) and pd.isna(ans_text)):
        return {"is_nonans": False, "is_refuse": False, "is_unable": False, "is_aftercall": False}

    ans = str(ans_text).strip()
    if ans == "":
        return {"is_nonans": False, "is_refuse": False, "is_unable": False, "is_aftercall": False}

    res = non_answers([ans]) or []
    cats = []
    for item in res:
        rid = extract_regex_id(item)
        if rid is None:
            continue
        cat = regex_id_to_category(rid)
        if cat is not None:
            cats.append(cat)

    s = set(cats)
    is_refuse = "REFUSE" in s
    is_unable = "UNABLE" in s
    is_aftercall = "AFTERCALL" in s
    is_nonans = len(s.intersection(set(types))) > 0

    return {
        "is_nonans": is_nonans,
        "is_refuse": is_refuse,
        "is_unable": is_unable,
        "is_aftercall": is_aftercall,
    }

def main():
   
    df = pd.read_excel(IN_PATH, engine="openpyxl")

    
    if "answer" not in df.columns:
        raise ValueError(f"can not find 'answer'。column name：{list(df.columns)}")

    res = df["answer"].apply(classify_answer)
    out = pd.concat([df.reset_index(drop=True), pd.json_normalize(res)], axis=1)
    out["non_answer"] = out["is_nonans"].astype(int)

    
    out.to_excel(OUT_XLSX, index=False)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    print("Saved:", OUT_XLSX)
    print("Saved:", OUT_CSV)
    print("Non-answer rate:", out["non_answer"].mean())

if __name__ == "__main__":
    main()
