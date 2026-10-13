"""Gerar a mesma chave de acesso da aplicacao; claims devem vir do IdP verificado."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crm.identity import make_viewer_key

parser = argparse.ArgumentParser()
parser.add_argument("--issuer", required=True)
parser.add_argument("--subject", required=True)
args = parser.parse_args()
print(make_viewer_key(args.issuer, args.subject))
