#!/usr/bin/env python3
"""腾讯混元生3D OpenAI 兼容接口客户端（仅标准库）

端点：https://api.ai3d.cloud.tencent.com/v1/ai3d/{submit,query}
Key：环境变量 HUNYUAN3D_API_KEY（或 --key 传入，勿入库）

用法：
  python hunyuan3d_api.py submit-image --image ak_ref.png --prompt "..." [--model 3.1]
  python hunyuan3d_api.py submit-text --prompt "一只小狗" [--model 3.0]
  python hunyuan3d_api.py query --job-id <JobId>
  python hunyuan3d_api.py poll --job-id <JobId> [--interval 8] [--timeout 900]
  python hunyuan3d_api.py download --job-id <JobId> --out dir/
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://api.ai3d.cloud.tencent.com"


def _post(path: str, payload: dict, api_key: str):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    req.add_header("Authorization", api_key)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:2000]}


def _key(args) -> str:
    k = args.key or os.environ.get("HUNYUAN3D_API_KEY", "")
    if not k:
        print("缺少 API Key：设置环境变量 HUNYUAN3D_API_KEY 或 --key", file=sys.stderr)
        sys.exit(2)
    return k


def _find(obj, *names):
    """在嵌套 dict 里按给定 key 名顺序取第一个存在的值。"""
    if isinstance(obj, dict):
        for n in names:
            if n in obj:
                return obj[n]
        for v in obj.values():
            r = _find(v, *names)
            if r is not None:
                return r
    return None


def cmd_submit_image(args) -> int:
    with open(args.image, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = args.image.rsplit(".", 1)[-1].lower()
    mime = "image/png" if ext in ("png", "webp") else "image/jpeg"
    if args.obj:
        payload = {"ImageUrl": {"Url": f"data:{mime};base64,{b64}"}, "Model": args.model}
    else:
        payload = {"ImageUrl": f"data:{mime};base64,{b64}", "Model": args.model}
    if args.prompt:
        payload["Prompt"] = args.prompt
    status, data = _post("/v1/ai3d/submit", payload, _key(args))
    print("status:", status)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if status in (200, 201) else 1


def cmd_submit_text(args) -> int:
    payload = {"Prompt": args.prompt, "Model": args.model}
    status, data = _post("/v1/ai3d/submit", payload, _key(args))
    print("status:", status)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if status in (200, 201) else 1


def cmd_query(args) -> int:
    status, data = _post("/v1/ai3d/query", {"JobId": args.job_id}, _key(args))
    print("status:", status)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if status == 200 else 1


def cmd_poll(args) -> int:
    deadline = time.time() + args.timeout
    last = None
    while time.time() < deadline:
        status, data = _post("/v1/ai3d/query", {"JobId": args.job_id}, _key(args))
        state = _find(data, "State", "Status", "status", "state")
        last = data
        print(f"[{time.strftime('%H:%M:%S')}] status={status} state={state}")
        if state in ("Succeed", "SUCCEED", "Success", "SUCCESS", "Done", "FINISHED", "completed"):
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0
        if state in ("Failed", "FAILED", "Error", "ERROR", "Cancelled"):
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 1
        time.sleep(args.interval)
    print("超时，最后状态：")
    print(json.dumps(last, ensure_ascii=False, indent=2))
    return 1


def _find_urls(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = k.lower()
            if isinstance(v, str) and v.startswith("http") and any(
                s in kl or s in v.lower()
                for s in ("url", "glb", "obj", "fbx", "file", "mesh", "download")
            ):
                out.append((k, v))
            else:
                _find_urls(v, out)
    elif isinstance(obj, list):
        for it in obj:
            _find_urls(it, out)


def cmd_download(args) -> int:
    status, data = _post("/v1/ai3d/query", {"JobId": args.job_id}, _key(args))
    if status != 200:
        print("query failed:", status)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 1
    found = []
    _find_urls(data, found)
    if not found:
        print("未在响应中找到下载 URL，响应如下：")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 1
    os.makedirs(args.out, exist_ok=True)
    for name, url in found:
        fn = url.split("?")[0].rsplit("/", 1)[-1]
        if not fn:
            fn = f"{args.job_id}_{name}.bin"
        dest = os.path.join(args.out, fn)
        print("下载", url[:120], "→", dest)
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
                f.write(r.read())
            print("OK", dest, os.path.getsize(dest), "bytes")
        except Exception as e:
            print("下载失败:", e)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="混元生3D OpenAI 兼容接口客户端")
    p.add_argument("--key", default=None, help="API Key（默认读 HUNYUAN3D_API_KEY）")
    sub = p.add_subparsers(dest="cmd", required=True)

    si = sub.add_parser("submit-image")
    si.add_argument("--image", required=True)
    si.add_argument("--prompt", default=None)
    si.add_argument("--model", default="3.1", choices=["3.0", "3.1"])
    si.add_argument("--obj", action="store_true", help="ImageUrl 用 {Url:...} 对象（实测接口用纯字符串）")
    si.set_defaults(func=cmd_submit_image)

    st = sub.add_parser("submit-text")
    st.add_argument("--prompt", required=True)
    st.add_argument("--model", default="3.0", choices=["3.0", "3.1"])
    st.set_defaults(func=cmd_submit_text)

    q = sub.add_parser("query")
    q.add_argument("--job-id", required=True)
    q.set_defaults(func=cmd_query)

    po = sub.add_parser("poll")
    po.add_argument("--job-id", required=True)
    po.add_argument("--interval", type=float, default=8.0)
    po.add_argument("--timeout", type=float, default=900.0)
    po.set_defaults(func=cmd_poll)

    dl = sub.add_parser("download")
    dl.add_argument("--job-id", required=True)
    dl.add_argument("--out", required=True)
    dl.set_defaults(func=cmd_download)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
