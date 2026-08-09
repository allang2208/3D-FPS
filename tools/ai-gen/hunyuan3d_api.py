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


def cmd_tokenhub_image(args) -> int:
    """TokenHub（新平台）OpenAI 兼容 images/generations 图生3D。"""
    base = args.base.rstrip("/")
    with open(args.image, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {
        "model": args.model,
        "mode": "image_to_3d",
        "image": b64,
        "format": args.format,
    }
    if args.texture:
        payload["texture"] = args.texture
    if args.prompt:
        payload["prompt"] = args.prompt
    req = urllib.request.Request(
        base + "/images/generations",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    req.add_header("Authorization", "Bearer " + _key(args))
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            status = resp.status
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", "replace")
        try:
            data = json.loads(body)
        except Exception:
            data = {"raw": body[:2000]}
    print("status:", status)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if status == 200 else 1


def _tokenhub_post(path: str, payload: dict, api_key: str):
    req = urllib.request.Request(
        "https://tokenhub.tencentmaas.com" + path,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    req.add_header("Authorization", "Bearer " + api_key)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:2000]}


def cmd_tokenhub_submit(args) -> int:
    """TokenHub 官方 3D submit（snake_case，模型名 hy-3d-3.0/3.1/express）。"""
    payload = {"model": args.model}
    if args.prompt:
        payload["prompt"] = args.prompt
    if args.image:
        with open(args.image, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        payload["image_base64"] = b64
    if args.generate_type:
        payload["generate_type"] = args.generate_type
    if args.enable_pbr:
        payload["enable_pbr"] = True
    if args.face_count:
        payload["face_count"] = args.face_count
    if args.result_format:
        payload["result_format"] = args.result_format
    status, data = _tokenhub_post("/v1/api/3d/submit", payload, _key(args))
    print("status:", status)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if status == 200 and isinstance(data, dict) and data.get("id"):
        print("JOB_ID=", data["id"])
    return 0 if status == 200 else 1


def cmd_tokenhub_query(args) -> int:
    status, data = _tokenhub_post(
        "/v1/api/3d/query", {"model": args.model, "id": args.job_id}, _key(args)
    )
    print("status:", status)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if status == 200 else 1


def cmd_tokenhub_poll(args) -> int:
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        status, data = _tokenhub_post(
            "/v1/api/3d/query", {"model": args.model, "id": args.job_id}, _key(args)
        )
        st = data.get("status", "") if isinstance(data, dict) else ""
        print(f"[{time.strftime('%H:%M:%S')}] status={st}")
        if st == "completed":
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0
        if st in ("failed", "error", "cancelled", "canceled"):
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 1
        time.sleep(args.interval)
    print("超时")
    return 1


def cmd_tokenhub_download(args) -> int:
    status, data = _tokenhub_post(
        "/v1/api/3d/query", {"model": args.model, "id": args.job_id}, _key(args)
    )
    if status != 200 or not isinstance(data, dict) or data.get("status") != "completed":
        print("任务未完成：")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 1
    os.makedirs(args.out, exist_ok=True)
    for item in data.get("data", []):
        url = item.get("url")
        if not url:
            continue
        fn = url.split("?")[0].rsplit("/", 1)[-1] or f"{args.job_id}.{item.get('type', 'bin')}"
        dest = os.path.join(args.out, fn)
        print("下载", url[:120], "→", dest)
        try:
            with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
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

    th = sub.add_parser("tokenhub-image")
    th.add_argument("--image", required=True)
    th.add_argument("--prompt", default=None)
    th.add_argument("--model", default="hunyuan-3d")
    th.add_argument("--format", default="glb", choices=["glb", "obj", "fbx", "stl"])
    th.add_argument("--texture", default="pbr", choices=["pbr", "flat"])
    th.add_argument(
        "--base",
        default="https://tokenhub.tencentcloudapi.com/v1",
        help="TokenHub base_url",
    )
    th.set_defaults(func=cmd_tokenhub_image)

    ts = sub.add_parser("tokenhub-submit")
    ts.add_argument("--model", default="hy-3d-3.1", choices=["hy-3d-3.0", "hy-3d-3.1", "hy-3d-express"])
    ts.add_argument("--prompt", default=None)
    ts.add_argument("--image", default=None)
    ts.add_argument("--generate-type", default=None, help="Normal/LowPoly/Geometry/Sketch")
    ts.add_argument("--enable-pbr", action="store_true")
    ts.add_argument("--face-count", type=int, default=None)
    ts.add_argument("--result-format", default=None, help="OBJ/GLB/STL/FBX/USDZ（大写）")
    ts.set_defaults(func=cmd_tokenhub_submit)

    tq = sub.add_parser("tokenhub-query")
    tq.add_argument("--model", default="hy-3d-3.1", choices=["hy-3d-3.0", "hy-3d-3.1", "hy-3d-express"])
    tq.add_argument("--job-id", required=True)
    tq.set_defaults(func=cmd_tokenhub_query)

    tp = sub.add_parser("tokenhub-poll")
    tp.add_argument("--model", default="hy-3d-3.1", choices=["hy-3d-3.0", "hy-3d-3.1", "hy-3d-express"])
    tp.add_argument("--job-id", required=True)
    tp.add_argument("--interval", type=float, default=10.0)
    tp.add_argument("--timeout", type=float, default=1200.0)
    tp.set_defaults(func=cmd_tokenhub_poll)

    td = sub.add_parser("tokenhub-download")
    td.add_argument("--model", default="hy-3d-3.1", choices=["hy-3d-3.0", "hy-3d-3.1", "hy-3d-express"])
    td.add_argument("--job-id", required=True)
    td.add_argument("--out", required=True)
    td.set_defaults(func=cmd_tokenhub_download)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
