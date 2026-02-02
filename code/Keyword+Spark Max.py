import re
import json
import time
import base64
import hmac
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode, urlparse
from email.utils import formatdate, parsedate_to_datetime

import pandas as pd
import websocket  # pip install websocket-client

import sys
sys.path.append(r"D:\2025_26 Spring\mnsc.2023.03253\1_code")
import kw_logic


# 0) path and keys
APP_ID = "eaf7df35"
API_KEY = "MY KEY"             #In this project, we use real api keys. This is only a temporary replacement.
API_SECRET = "SECRET"          #In this project, we use real api keys. This is only a temporary replacement.

for name, val in [("APP_ID", APP_ID), ("API_KEY", API_KEY), ("API_SECRET", API_SECRET)]:
    if not val or val.strip() == "" or "substitute" in val:
        raise ValueError(f"{name} Not filled in correctly：please subtitute {name} into the real value")

APP_ID = APP_ID.strip()
API_KEY = API_KEY.strip()
API_SECRET = API_SECRET.strip()



# 1) Spark Max 
SPARK_URL = "wss://spark-api.xf-yun.com/v3.5/chat"
SPARK_DOMAIN = "generalv3.5"  # Spark Max



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



# 3) Generate authentication URL
def build_auth(ws_url: str, api_key: str, api_secret: str):
    u = urlparse(ws_url)
    host = u.netloc
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



# 4)  Spark

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
        if debug_time:
            server_date = None
            try:
                server_date = (e.resp_headers or {}).get("date") or (e.resp_headers or {}).get("Date")
            except Exception:
                server_date = None
            print("[AUTH] handshake failed.")
            print("       client date_str:", date_str)
            if server_date:
                print("       server date    :", server_date)
                try:
                    dt_client = parsedate_to_datetime(date_str)
                    dt_server = parsedate_to_datetime(server_date)
                    skew_sec = abs((dt_client - dt_server).total_seconds())
                    print(f"       |client-server| skew_sec = {skew_sec:.1f}")
                except Exception:
                    pass
        raise

    req = {
        "header": {"app_id": APP_ID, "uid": uid},
        "parameter": {
            "chat": {
                "domain": SPARK_DOMAIN,
                "temperature": float(temperature),
                "max_tokens": int(max_tokens),
            }
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


def coerce_01(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return pd.NA
    try:
        v = int(str(x).strip())
        return 1 if v == 1 else 0
    except Exception:
        return pd.NA



# 6) parallel

class StartRateLimiter:
    def __init__(self, min_interval_sec: float):
        self.min_interval_sec = float(min_interval_sec)
        self._lock = threading.Lock()
        self._next_time = 0.0

    def wait_turn(self):
        with self._lock:
            now = time.time()
            sleep_sec = max(0.0, self._next_time - now)
            self._next_time = max(now, self._next_time) + self.min_interval_sec
        if sleep_sec > 0:
            time.sleep(sleep_sec)



# 7) Spark Worker
def spark_worker(row_i, tid, q, a, rate_limiter: StartRateLimiter, max_retry: int, timeout_sec: int):
    prompt = make_prompt(q, a, comments="N/A")
    last_err = None

    for attempt in range(max_retry + 1):
        try:
            rate_limiter.wait_turn()
            raw = spark_chat_once(
                prompt,
                uid=f"tid_{tid}_row_{row_i}",
                timeout_sec=timeout_sec,
            )
            parsed, err, extracted = parse_model_json(raw)
            if err:
                return {
                    "row": row_i,
                    "spark_raw": raw,
                    "spark_json_extracted": extracted,
                    "spark_assessment": "",
                    "spark_pred_nonanswer": pd.NA,
                    "spark_parse_error": err,
                }
            pred = coerce_01(parsed.get("your_classification", pd.NA))
            return {
                "row": row_i,
                "spark_raw": raw,
                "spark_json_extracted": extracted,
                "spark_assessment": parsed.get("assessment", ""),
                "spark_pred_nonanswer": pred,
                "spark_parse_error": "",
            }
        except Exception as e:
            last_err = repr(e)
            
            time.sleep(1.0 + 0.7 * attempt)

    return {
        "row": row_i,
        "spark_raw": "",
        "spark_json_extracted": "",
        "spark_assessment": "",
        "spark_pred_nonanswer": pd.NA,
        "spark_parse_error": f"call_failed: {last_err}",
    }



# 8) Main program（kw_match==0 -> final=0；kw_match==1 -> Spark）

def main():
    in_path = r"D:\2025_26 Spring\Replication\Q&A_with_nonanswer.xlsx"
    out_path = r"D:\2025_26 Spring\Replication\Q&A_with_nonanswer__AUTHORLOGIC__kw0_is0__sparkmax_parallel.xlsx"

    
    USE_FUTURE_KW = True  # True: kw_dict_with_future，False: kw_dict

    
    MAX_WORKERS = 20              
    START_INTERVAL_SEC = 0.08     
    SPARK_TIMEOUT_SEC = 60
    MAX_RETRY = 1

    
    CHECKPOINT_EVERY_DONE = 40    

    kw_dict = kw_logic.kw_dict_with_future if USE_FUTURE_KW else kw_logic.kw_dict

    print("=" * 90)
    print("[START] Loading Excel")
    df = pd.read_excel(in_path, engine="openpyxl")
    print(f"[OK] rows={len(df):,}, cols={len(df.columns)}")
    print("[INFO] columns:", list(df.columns))

    required = {"transcriptid", "question", "answer"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Excel missing necessary columns：{missing}。must contain：{required}")

    # output columns: KW + final
    for c, d in {
        "kw_match": pd.NA,
        "kw_matches": "",
        "used_spark": pd.NA,            # 1=useSpark; 0=jump over
        "final_pred_nonanswer": pd.NA,  
    }.items():
        if c not in df.columns:
            df[c] = d

    
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
    print("[SMOKE] auth smoke test")
    _ = spark_chat_once('only reply one JSON：{"ok":true}', uid="smoke_test", max_tokens=50, temperature=0.0, timeout_sec=30)
    print("[SMOKE] OK")

    print("=" * 90)
    print("[STEP A] KW prefilter (serial)")
    tasks = []
    skipped_as_zero = 0  # kw_match==0 => final=0，jump over Spark

    for k, i in enumerate(df.index, start=1):
        tid = df.at[i, "transcriptid"]
        q = str(df.at[i, "question"]).strip()
        a = str(df.at[i, "answer"]).strip()

        try:
            match, matches = kw_logic.find_kw_matches(a, kw_dict=kw_dict)
        except Exception as e:
            match, matches = False, []
            df.at[i, "kw_matches"] = f"kw_error:{repr(e)}"

        df.at[i, "kw_match"] = int(bool(match))
        if matches and isinstance(matches, list):
            df.at[i, "kw_matches"] = ";".join(sorted(set(matches)))

        
        if not match:
            df.at[i, "used_spark"] = 0
            df.at[i, "final_pred_nonanswer"] = 0
            skipped_as_zero += 1
        else:
            # kw_match==1 -> need Spark to decide 0/1
            df.at[i, "used_spark"] = 1
            tasks.append((i, tid, q, a))

        if k % 200 == 0:
            print(f"[KW] {k}/{len(df)} | kw0->0 skipped={skipped_as_zero} | queued_spark={len(tasks)}")

    print("=" * 90)
    print(f"[STEP B] Spark Max (parallel) | queued={len(tasks)} | workers={MAX_WORKERS}")

    rate_limiter = StartRateLimiter(START_INTERVAL_SEC)

    done = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [
            ex.submit(spark_worker, i, tid, q, a, rate_limiter, MAX_RETRY, SPARK_TIMEOUT_SEC)
            for (i, tid, q, a) in tasks
        ]

        for fut in as_completed(futures):
            res = fut.result()
            i = res["row"]

            df.at[i, "spark_raw"] = res["spark_raw"]
            df.at[i, "spark_json_extracted"] = res["spark_json_extracted"]
            df.at[i, "spark_assessment"] = res["spark_assessment"]
            df.at[i, "spark_pred_nonanswer"] = res["spark_pred_nonanswer"]
            df.at[i, "spark_parse_error"] = res["spark_parse_error"]

            # kw_match==1 
            if pd.notna(df.at[i, "spark_pred_nonanswer"]):
                df.at[i, "final_pred_nonanswer"] = df.at[i, "spark_pred_nonanswer"]

            done += 1
            if done % 10 == 0:
                elapsed = time.time() - t0
                print(f"[SPARK] done {done}/{len(tasks)} | elapsed={elapsed:.1f}s | last_row={i} pred={df.at[i,'spark_pred_nonanswer']} err={df.at[i,'spark_parse_error']}")

            if done % CHECKPOINT_EVERY_DONE == 0:
                df.to_excel(out_path, index=False)
                print(f"[SAVE] checkpoint -> {out_path} | done={done}/{len(tasks)}")

    df.to_excel(out_path, index=False)
    print("\n[DONE] Saved:", out_path)
    print(f"[SUMMARY] total_rows={len(df)} | kw0->0 skipped={skipped_as_zero} | spark_called={len(tasks)}")
    if len(df) > 0:
        print(f"[SUMMARY] call_rate={(len(tasks)/len(df)):.1%} | skipped_rate={(skipped_as_zero/len(df)):.1%}")


if __name__ == "__main__":
    main()
