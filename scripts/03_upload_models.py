"""
scripts/03_upload_models.py
Upload locally trained model files to Supabase Storage
and update model_configs table.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import supabase_client as db
from src.utils.config import SUPABASE_STORAGE_BUCKET, get_model_config
from src.utils.logger import get_logger
from src.utils.supabase_client import get_client

log = get_logger("upload_models")

LOTTERY_TYPES = ["power_655", "mega_645", "lotto_535"]
MODEL_FILES = {
    "lstm": "lstm.h5",
    "xgboost": "xgboost.pkl",
    "markov": "markov.pkl",
}


def upload_models(lottery_type: str, version: str, local_dir: Path) -> None:
    log.info(f"Uploading models for {lottery_type} v{version} from {local_dir}")
    supabase = get_client()

    for model_name, filename in MODEL_FILES.items():
        local_path = local_dir / filename
        if not local_path.exists():
            log.warning(f"File not found: {local_path}, skipping.")
            continue

        remote_path = f"models/v{version}/{lottery_type}/{filename}"

        with open(local_path, "rb") as f:
            data = f.read()

        try:
            supabase.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
                remote_path, data, {"upsert": "true"}
            )
            log.info(f"Uploaded: {remote_path} ({len(data):,} bytes)")
        except Exception as exc:
            log.error(f"Upload failed {remote_path}: {exc}")
            continue

    # Update model_configs table
    config = get_model_config(lottery_type)
    base_weights = config["ensemble"]["weights"]

    for model_name in ["lstm", "xgboost", "statistical"]:
        weight = base_weights.get(model_name, 0.33)
        params = config.get(model_name if model_name != "statistical" else "statistical", {})
        # Deactivate old configs
        db.deactivate_old_configs(lottery_type, model_name)
        # Insert new config
        get_client().table("model_configs").upsert({
            "lottery_type": lottery_type,
            "model_name": model_name,
            "parameters": params,
            "ensemble_weight": weight,
            "version": version,
            "is_active": True,
        }, on_conflict="lottery_type, model_name, version").execute()
        log.info(f"model_configs updated: {lottery_type}/{model_name} v{version}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lottery", choices=LOTTERY_TYPES + ["all"], default="all")
    parser.add_argument("--version", default="3.0")
    parser.add_argument("--input", default="models", help="Local models directory")
    args = parser.parse_args()

    targets = LOTTERY_TYPES if args.lottery == "all" else [args.lottery]
    for lt in targets:
        local_dir = Path(args.input) / f"v{args.version}" / lt
        upload_models(lt, args.version, local_dir)

    log.info("Upload complete.")


if __name__ == "__main__":
    main()
