"""Dungeon props 2026-09-20: FLUX.2 three-view reference sheets on the 5080 ComfyUI.

Subcommands:
  gen-refs  : submit txt2img jobs for every prop in props.json
  fetch-refs: poll jobs, download sheets into <prop>/three_views.png
  status    : print current queue/history state for owned jobs
"""
import json, sys, uuid, urllib.request, urllib.parse
from pathlib import Path

P = Path(__file__).resolve().parent.parent   # task root holds props.json
BASE = 'http://192.168.3.142:8188'
CLIENT = 'DungeonProps20260920'


def req(path, data=None, headers=None, timeout=120):
    return json.load(urllib.request.urlopen(
        urllib.request.Request(BASE + path, data=data, headers=headers or {}), timeout=timeout))


def build_flux2(prompt, seed, width=1536, height=1024, steps=24, guidance=4.0, prefix='DungeonProps20260920/ref'):
    # Mirrors the FLUX.2 Dev txt2img graph proven by the original project's comfyui-gen.py.
    nodes = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux2_dev_fp8mixed.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "mistral_3_small_flux2_fp4_mixed.safetensors", "type": "flux2"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": width, "height": height}},
        "7": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "9": {"class_type": "FluxGuidance", "inputs": {"conditioning": ["4", 0], "guidance": guidance}},
        "10": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["9", 0]}},
        "11": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "12": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["11", 0], "guider": ["10", 0], "sampler": ["8", 0],
            "sigmas": ["6", 0], "latent_image": ["7", 0]}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["3", 0]}},
        "14": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["13", 0]}},
    }
    return nodes


def main():
    props = json.loads((P / 'props.json').read_text(encoding='utf-8'))['props']
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'

    if cmd == 'gen-refs':
        for d in props:
            folder = P / d['id']
            folder.mkdir(exist_ok=True)
            receipt = folder / 'ref_receipt.json'
            if receipt.exists():
                print(d['id'], 'already submitted', flush=True)
                continue
            w = build_flux2(d['prompt'], d['seed'], prefix=f'DungeonProps20260920/{d["id"]}/three_views')
            (folder / 'ref_workflow.json').write_text(json.dumps(w, indent=2))
            r = req('/prompt', json.dumps({'client_id': CLIENT, 'prompt': w}).encode(),
                    {'Content-Type': 'application/json'})
            receipt.write_text(json.dumps(r, indent=2))
            print(d['id'], r, flush=True)

    elif cmd == 'fetch-refs':
        for d in props:
            folder = P / d['id']
            receipt = folder / 'ref_receipt.json'
            if not receipt.exists():
                print(d['id'], 'not submitted', flush=True)
                continue
            pid = json.loads(receipt.read_text())['prompt_id']
            h = req('/history/' + pid).get(pid)
            if not h:
                print(d['id'], 'pending', flush=True)
                continue
            (folder / 'ref_history.json').write_text(json.dumps(h, indent=2))
            print(d['id'], h['status']['status_str'], flush=True)
            if h['status']['status_str'] != 'success':
                for kind, msg in h['status']['messages']:
                    if kind == 'execution_error':
                        print('   ', msg.get('exception_message', '')[:300], flush=True)
                continue
            saved = h.get('outputs', {}).get('14', {}).get('images', [])
            for img in saved:
                out = folder / 'three_views.png'
                if not out.exists():
                    url = BASE + '/view?' + urllib.parse.urlencode(
                        {'filename': img['filename'], 'subfolder': img.get('subfolder', ''), 'type': img['type']})
                    urllib.request.urlretrieve(url, out)
                    print(d['id'], 'downloaded', out.name, flush=True)

    else:  # status
        q = req('/queue')
        print('running:', len(q.get('queue_running', [])), 'pending:', len(q.get('queue_pending', [])))
        for d in props:
            receipt = P / d['id'] / 'ref_receipt.json'
            print(' -', d['id'], 'submitted' if receipt.exists() else 'not-submitted')


if __name__ == '__main__':
    main()