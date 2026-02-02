# -*- coding: utf-8 -*-

import re
import json
import time
import base64
import hmac
import hashlib
import pandas as pd
from urllib.parse import urlencode, urlparse
from email.utils import formatdate, parsedate_to_datetime

import websocket  



APP_ID = "eaf7df35"
API_KEY = "MY KEY"        #In this project, we use real api keys. This is only a temporary replacement.
API_SECRET = "SECRET"     #In this project, we use api secret. This is only a temporary replacement.

for name, val in [("APP_ID", APP_ID), ("API_KEY", API_KEY), ("API_SECRET", API_SECRET)]:
    if not val or val.strip() == "" or "substitute" in val:
        raise ValueError(f"{name} Not filled in correctly：please subtitute {name} into the real value")

APP_ID = APP_ID.strip()
API_KEY = API_KEY.strip()
API_SECRET = API_SECRET.strip()



# 1) Spark Pro 
SPARK_URL = "wss://spark-api.xf-yun.com/v3.5/chat"
SPARK_DOMAIN = "generalv3.5"  # Spark Pro



# 2) Prompt
PROMPT_TEMPLATE = """Investor question:
{question}

Manager response:
{answer}

A research assistant has marked the above response as including a
statement that reflects unwillingness or inability to answer (part) of the
analysts' question, because of the following comment(s):
> {comments}

Based on the question and full response above, provide a detailed
assessment whether the manager's response includes a statement,
explanation, or justification indicating an inability or unwillingness to
answer the question. If you classify the response as reflecting inability
or unwillingness to answer, justify your classification with specific
phrases or sentences from the manager's response. If there's no such
indication, explain why not.

IMPORTANT OUTPUT RULES:
1) Output MUST be exactly ONE valid JSON object.
2) Do NOT include markdown code fences.
3) Do NOT include any extra text before or after the JSON.

Return JSON in this exact format:
{{
  "assessment": "a detailed assessment unique to this evaluation",
  "your_classification": 1
}}
"""


def make_prompt(question: str, answer: str, comments: str = "N/A") -> str:
    return PROMPT_TEMPLATE.format(
        question=(question or "").strip(),
        answer=(answer or "").strip(),
        comments=(comments or "N/A").strip(),
    )



# 3) genertae URL
def build_auth(ws_url: str, api_key: str, api_secret: str):
    """
    返回: (authed_url, date_str, host)
    """
    u = urlparse(ws_url)
    host = u.netloc  # more stable by using netloc 
    path = u.path

    
    date_str = formatdate(timeval=None, localtime=False, usegmt=True)

    signature_origin = f"host: {host}\n" f"date: {date_str}\n" f"GET {path} HTTP/1.1"

    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")

    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

    params = {"authorization": authorization, "date": date_str, "host": host}
    authed_url = ws_url + "?" + urlencode(params)
    return authed_url, date_str, host



# 4) Spark
def spark_chat_once(
    prompt: str,
    uid: str,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    timeout_sec: int = 60,
    debug_time: bool = False,
) -> str:
    authed_url, date_str, _host = build_auth(SPARK_URL, API_KEY, API_SECRET)

    if debug_time:
        print(f"[AUTH] client date_str = {date_str} (GMT RFC1123)")

    try:
        ws = websocket.create_connection(
            authed_url,
            timeout=timeout_sec,
            
            header=[f"X-Date: {date_str}"],
        )
    except websocket._exceptions.WebSocketBadStatusException as e:
        
        server_date = None
        try:
            # resp_headers 可能是 dict
            server_date = (e.resp_headers or {}).get("date") or (e.resp_headers or {}).get("Date")
        except Exception:
            server_date = None

        if debug_time:
            print("[AUTH] handshake failed.")
            print("       client date_str:", date_str)
            if server_date:
                print("       server date    :", server_date)
                try:
                    dt_client = parsedate_to_datetime(date_str)
                    dt_server = parsedate_to_datetime(server_date)
                    skew_sec = abs((dt_client - dt_server).total_seconds())
                    print(f"       |client-server| skew_sec = {skew_sec:.1f}")
                except Exception as _:
                    pass

        raise

    req = {
        "header": {"app_id": APP_ID, "uid": uid},
        "parameter": {
            "chat": {"domain": SPARK_DOMAIN, "temperature": float(temperature), "max_tokens": int(max_tokens)}
        },
        "payload": {"message": {"text": [{"role": "user", "content": prompt}]}},
    }

    ws.send(json.dumps(req, ensure_ascii=False))

    chunks = []
    try:
        while True:
            raw = ws.recv()
            msg = json.loads(raw)

            code = msg.get("header", {}).get("code", -1)
            if code != 0:
                raise RuntimeError(
                    f"Spark API error code={code}, message={msg.get('header', {}).get('message')}"
                )

            choices = msg.get("payload", {}).get("choices", {})
            status = choices.get("status", 0)
            for t in choices.get("text", []):
                if isinstance(t, dict) and "content" in t:
                    chunks.append(t["content"])

            if status == 2:
                break
    finally:
        ws.close()

    return "".join(chunks).strip()



# 5) JSON 
def parse_model_json(text: str):
    if not text or str(text).strip() == "":
        return None, "empty_response", ""

    try:
        return json.loads(text), None, text
    except Exception:
        pass

    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None, "no_json_object_found", text

    cand = m.group(0).strip()
    try:
        return json.loads(cand), None, cand
    except Exception as e:
        return None, f"json_parse_failed: {repr(e)}", cand


def safe_preview(s: str, n: int = 220) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\n", " ").replace("\r", " ")
    return (s[:n] + " ...") if len(s) > n else s



# 6) evaluation

def eval_binary(y_true, y_pred):
    y_true = pd.Series(y_true).astype(int).values
    y_pred = pd.Series(y_pred).astype(int).values

    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())

    acc = (tp + tn) / max(1, (tp + tn + fp + fn))
    prec = tp / max(1, (tp + fp))
    rec = tp / max(1, (tp + fn))
    f1 = 2 * prec * rec / max(1e-12, (prec + rec))
    return {"TP": tp, "TN": tn, "FP": fp, "FN": fn, "Accuracy": acc, "Precision": prec, "Recall": rec, "F1": f1}



# 7) Main program
def main():
    in_path = r"D:\2025_26 Spring\Replication\Q&A_with_nonanswer.xlsx"
    out_path = r"D:\2025_26 Spring\Replication\Q&A_with_nonanswer__sparkpro_scored.xlsx"

    SLEEP_BETWEEN_CALLS_SEC = 0.25
    CHECKPOINT_EVERY_N = 20
    MAX_RETRY = 1

    print("=" * 90)
    print("[START] Loading Excel")
    df = pd.read_excel(in_path, engine="openpyxl")
    print(f"[OK] rows={len(df):,}, cols={len(df.columns)}")
    print("[INFO] columns:", list(df.columns))

    required = {"transcriptid", "question", "answer"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Excel missing necessary columns：{missing}。must contain：{required}")

    
    for c, d in {
        "spark_raw": "",
        "spark_json_extracted": "",
        "spark_assessment": "",
        "spark_pred_nonanswer": pd.NA,
        "spark_parse_error": "",
    }.items():
        if c not in df.columns:
            df[c] = d

    print("=" * 90)
    print("[SMOKE] auth smoke test (Only Authentication Test)")
    try:
        raw = spark_chat_once('just reply one JSON：{"ok":true}', uid="smoke_test", max_tokens=50, temperature=0.0, debug_time=True)
        print("[SMOKE] success, raw:", safe_preview(raw, 200))
    except Exception as e:
        print("[SMOKE] failed:", repr(e))
        print("         If you see a large skew_sec value: Please set your Windows time to automatic synchronization (error should be <300 seconds).")
        return

    print("=" * 90)
    print("[RUN] Calling Spark Pro ...")
    t0 = time.time()

    for k, i in enumerate(df.index, start=1):
        tid = df.at[i, "transcriptid"]
        q = str(df.at[i, "question"]).strip()
        a = str(df.at[i, "answer"]).strip()

        print(f"\n[PROGRESS] {k}/{len(df)} row={i} transcriptid={tid} q_len={len(q)} a_len={len(a)}")

        prompt = make_prompt(q, a, comments="N/A")

        raw = None
        last_err = None

        for attempt in range(MAX_RETRY + 1):
            try:
                raw = spark_chat_once(prompt, uid=f"transcript_{tid}", debug_time=False)
                break
            except Exception as e:
                last_err = repr(e)
                print(f"[ERROR] call_failed attempt={attempt+1}/{MAX_RETRY+1} -> {last_err}")
                time.sleep(1.0)

        if raw is None:
            df.at[i, "spark_parse_error"] = f"call_failed: {last_err}"
            continue

        df.at[i, "spark_raw"] = raw
        print("[OK] raw_head:", safe_preview(raw, 220))

        parsed, err, extracted = parse_model_json(raw)
        df.at[i, "spark_json_extracted"] = extracted
        df.at[i, "spark_parse_error"] = err or ""

        if err:
            print("[WARN] JSON parse error:", err)
        else:
            df.at[i, "spark_assessment"] = parsed.get("assessment", "")
            df.at[i, "spark_pred_nonanswer"] = parsed.get("your_classification", pd.NA)
            print("[OK] pred_nonanswer =", df.at[i, "spark_pred_nonanswer"])

        if k % CHECKPOINT_EVERY_N == 0:
            df.to_excel(out_path, index=False)
            print(f"[SAVE] checkpoint -> {out_path}  elapsed={time.time()-t0:.1f}s")

        time.sleep(SLEEP_BETWEEN_CALLS_SEC)

    df.to_excel(out_path, index=False)
    print("\n[DONE] Saved:", out_path)

    
    if "non_answer" in df.columns:
        eval_df = df.dropna(subset=["non_answer", "spark_pred_nonanswer"]).copy()
        if len(eval_df) > 0:
            m = eval_binary(eval_df["non_answer"], eval_df["spark_pred_nonanswer"])
            print("\n[EVAL] vs non_answer")
            print(f"n={len(eval_df)} TP={m['TP']} TN={m['TN']} FP={m['FP']} FN={m['FN']}")
            print(f"Accuracy={m['Accuracy']:.4f} Precision={m['Precision']:.4f} Recall={m['Recall']:.4f} F1={m['F1']:.4f}")


if __name__ == "__main__":
    main()
