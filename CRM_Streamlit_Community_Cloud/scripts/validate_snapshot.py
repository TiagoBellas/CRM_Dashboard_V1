"""Valida estrutura/atestados e hash. Não certifica equivalencia de cálculos."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from crm.contracts import load_manifest, payload_digest, validate_payload

parser = argparse.ArgumentParser()
parser.add_argument("path", type=Path)
parser.add_argument("--release", required=True)
args = parser.parse_args()
raw = args.path.read_text(encoding="utf-8")
validate_payload(raw, load_manifest(ROOT), "databricks", args.release)
print("Estrutura e atestados válidos; comparar com o Power BI continua obrigatório.")
print("payload_sha256:", payload_digest(raw))
