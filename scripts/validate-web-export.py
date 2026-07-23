from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"src", "href"} and value:
                self._add_asset(value)

    def _add_asset(self, value: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme or parsed.netloc or value.startswith("#") or value.startswith("data:"):
            return
        path = parsed.path.lstrip("/")
        if path:
            self.assets.add(path)


def fail(message: str) -> None:
    print(f"Web export validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_vercel_config(path: Path) -> dict[str, object]:
    if not path.is_file():
        fail(f"{path} does not exist")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")


def referenced_assets_from_html(entry_path: Path) -> set[str]:
    html = entry_path.read_text(encoding="utf-8")
    parser = AssetParser()
    parser.feed(html)

    for match in re.finditer(r'''["']([^"']+\.(?:wasm|pck|js|worker\.js|png|ico|svg|css))["']''', html):
        value = match.group(1)
        parsed = urlparse(value)
        if not parsed.scheme and not parsed.netloc and not value.startswith("data:"):
            parser.assets.add(parsed.path.lstrip("/"))

    return parser.assets


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the generated Godot Web export and Vercel config.")
    parser.add_argument("--output-dir", default="build/web")
    parser.add_argument("--entry-html", default="index.html")
    parser.add_argument("--vercel-config", default="vercel.json")
    args = parser.parse_args()

    output_dir = (ROOT / args.output_dir).resolve()
    entry_path = output_dir / args.entry_html
    vercel_config_path = ROOT / args.vercel_config

    if not output_dir.is_dir():
        fail(f"expected output directory {output_dir} to exist")
    if not entry_path.is_file():
        fail(f"expected entry HTML {entry_path} to exist")

    config = load_vercel_config(vercel_config_path)
    if config.get("buildCommand") != "bash scripts/export-web.sh":
        fail("vercel.json buildCommand must be 'bash scripts/export-web.sh'")
    if config.get("outputDirectory") != args.output_dir.replace("\\", "/"):
        fail(f"vercel.json outputDirectory must be '{args.output_dir}'")

    required_suffixes = {".html", ".js", ".wasm", ".pck"}
    existing_suffixes = {path.suffix for path in output_dir.iterdir() if path.is_file()}
    missing_suffixes = sorted(required_suffixes - existing_suffixes)
    if missing_suffixes:
        fail(f"missing expected generated asset types: {', '.join(missing_suffixes)}")

    assets = referenced_assets_from_html(entry_path)
    missing_assets = sorted(asset for asset in assets if not (output_dir / asset).is_file())
    if missing_assets:
        fail("entry HTML references missing assets: " + ", ".join(missing_assets))

    print(f"Validated Godot Web export in {output_dir.relative_to(ROOT)} with entry {args.entry_html}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
