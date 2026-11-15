import subprocess
import logging
import shutil
import socket
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ModelDownloader")

REPO_ID = "google/embeddinggemma-2"
TARGET_DIR = Path("models/embeddinggemma-2")

FILES_TO_DOWNLOAD = [
    "config.json",
    "config_sentence_transformers.json",
    "sentence_bert_config.json",
    "modules.json",
    "tokenizer.json",
    "tokenizer.model",
    "tokenizer_config.json",
    "preprocessor_config.json",
    "processor_config.json",
    "chat_template.jinja",
    "1_Pooling/config.json",
    "2_Normalize/config.json",
    "model.safetensors"
]

def detect_proxy() -> Optional[str]:
    """Auto-detects if local proxy (127.0.0.1:10808) is active."""
    try:
        s = socket.socket()
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", 10808)) == 0:
            s.close()
            return "http://127.0.0.1:10808"
        s.close()
    except Exception:
        pass
    return None

def download_file(filename: str, target_dir: Path, proxy: Optional[str] = None):
    out_file = target_dir / filename
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if out_file.exists() and out_file.stat().st_size > 0 and filename != "model.safetensors":
        logger.info("File '%s' already exists (%d bytes). Skipping.", filename, out_file.stat().st_size)
        return

    url = f"https://huggingface.co/{REPO_ID}/resolve/main/{filename}"
    logger.info("Downloading %s ...", filename)

    curl_bin = shutil.which("curl") or "curl"
    cmd = [curl_bin]
    if proxy:
        cmd.extend(["-x", proxy])
    cmd.extend([
        "-L",
        "-C", "-", # Resumable download
        "--retry", "5",
        "--retry-delay", "3",
        "-o", str(out_file),
        url
    ])

    res = subprocess.run(cmd)
    if res.returncode == 0:
        logger.info("Successfully downloaded '%s' (%d bytes).", filename, out_file.stat().st_size)
    else:
        logger.error("Failed to download '%s' (exit code %d)", filename, res.returncode)

def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    proxy = detect_proxy()
    if proxy:
        logger.info("Detected active proxy: %s", proxy)
    else:
        logger.info("No local proxy detected. Downloading directly.")

    logger.info("Starting download of '%s' into %s...", REPO_ID, TARGET_DIR)

    for fn in FILES_TO_DOWNLOAD:
        download_file(fn, TARGET_DIR, proxy)

    logger.info("Model download process completed!")

if __name__ == "__main__":
    main()
