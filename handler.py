"""
PanoWan RunPod Serverless Handler
Generates 360 panoramic videos from text prompts using PanoWan.
"""

import sys
import traceback

print("=== PanoWan Handler Starting ===", flush=True)
print(f"Python version: {sys.version}", flush=True)

try:
    print("Importing runpod...", flush=True)
    import runpod
    print(f"runpod imported ok", flush=True)
except Exception as e:
    print(f"FATAL: Failed to import runpod: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

import subprocess
import os
import base64

print("All imports successful", flush=True)

# Check that model files exist
wan_path = "/app/PanoWan/models/Wan-AI/Wan2.1-T2V-1.3B"
lora_path = "/app/PanoWan/models/PanoWan/latest-lora.ckpt"

print(f"Checking Wan model path: {wan_path}", flush=True)
print(f"  Exists: {os.path.exists(wan_path)}", flush=True)
if os.path.exists(wan_path):
    print(f"  Contents: {os.listdir(wan_path)[:10]}", flush=True)

print(f"Checking LoRA path: {lora_path}", flush=True)
print(f"  Exists: {os.path.exists(lora_path)}", flush=True)

# Check PanoWan directory
panowan_dir = "/app/PanoWan"
print(f"PanoWan dir exists: {os.path.exists(panowan_dir)}", flush=True)
if os.path.exists(panowan_dir):
    print(f"PanoWan contents: {os.listdir(panowan_dir)[:15]}", flush=True)
    models_dir = os.path.join(panowan_dir, "models")
    if os.path.exists(models_dir):
        print(f"Models dir contents: {os.listdir(models_dir)}", flush=True)

# Check uv is available
uv_check = subprocess.run(["which", "uv"], capture_output=True, text=True)
print(f"uv location: {uv_check.stdout.strip() or 'NOT FOUND'}", flush=True)


def handler(event):
    try:
        print(f"=== Job received: {event.get('id', 'unknown')} ===", flush=True)
        job_input = event["input"]
        prompt = job_input.get("prompt", "A beautiful mountain landscape at sunset")
        print(f"Prompt: {prompt[:100]}", flush=True)

        output_path = f"/tmp/output_{event['id']}.mp4"

        cmd = [
            "uv", "run", "panowan-test",
            "--wan-model-path", "./models/Wan-AI/Wan2.1-T2V-1.3B",
            "--lora-checkpoint-path", "./models/PanoWan/latest-lora.ckpt",
            "--output-path", output_path,
            "--prompt", prompt
        ]

        print(f"Running command: {' '.join(cmd)}", flush=True)

        result = subprocess.run(
            cmd,
            cwd="/app/PanoWan",
            capture_output=True,
            text=True,
            timeout=600
        )

        print(f"Return code: {result.returncode}", flush=True)
        print(f"Stdout: {result.stdout[-500:]}", flush=True)
        print(f"Stderr: {result.stderr[-500:]}", flush=True)

        if result.returncode != 0:
            return {"error": f"Generation failed: {result.stderr[-500:]}"}

        if not os.path.exists(output_path):
            return {"error": "Output file not created"}

        with open(output_path, "rb") as f:
            video_bytes = f.read()

        video_base64 = base64.b64encode(video_bytes).decode("utf-8")
        os.remove(output_path)

        print(f"=== Job complete, video size: {len(video_bytes)} bytes ===", flush=True)

        return {
            "video_base64": video_base64,
            "prompt": prompt,
            "format": "mp4"
        }

    except subprocess.TimeoutExpired:
        print("ERROR: Generation timed out", flush=True)
        return {"error": "Generation timed out after 10 minutes"}
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        traceback.print_exc()
        return {"error": str(e)}


print("=== Registering handler with RunPod ===", flush=True)
runpod.serverless.start({"handler": handler})
