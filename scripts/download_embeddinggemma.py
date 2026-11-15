import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ModelDownloader")

REPO_ID = "google/embeddinggemma-2"
TARGET_DIR = Path("models/embeddinggemma-2")
PROXY = "http://127.0.0.1:10808"

FILES_TO_DOWNLOAD = [
    "config.json",
    "config_sentence_transformers.json",
    "sentence_bert_config.json",
    "modules.json",
    "tokenizer.json",
    "tokenizer.model",
    "tokenizer_config.json",
    "1_Pooling/config.json",
    "2_Normalize/config.json",
    "model.safetensors"
]

def download_file(filename: str, target_dir: Path, proxy: str = PROXY):
    out_file = target_dir / filename
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if out_file.exists() and out_file.stat().st_size > 0 and filename != "model.safetensors":
        logger.info("File '%s' already exists (%d bytes). Skipping.", filename, out_file.stat().st_size)
        return

    url = f"https://huggingface.co/{REPO_ID}/resolve/main/{filename}"
    logger.info("Downloading %s ...", filename)

    cmd = [
        "curl.exe",
        "-x", proxy,
        "-L",
        "-C", "-", # Resumable download!
        "--retry", "5",
        "--retry-delay", "3",
        "-o", str(out_file),
        url
    ]

    res = subprocess.run(cmd)
    if res.returncode == 0:
        logger.info("Successfully downloaded '%s' (%d bytes).", filename, out_file.stat().st_size)
    else:
        logger.error("Failed to download '%s' (exit code %d)", filename, res.returncode)

def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Starting download of '%s' into %s via %s...", REPO_ID, TARGET_DIR, PROXY)

    for fn in FILES_TO_DOWNLOAD:
        download_file(fn, TARGET_DIR, PROXY)

    logger.info("Model download process completed!")

if __name__ == "__main__":
    main()
