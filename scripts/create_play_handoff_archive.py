#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDOFF = ROOT / "build/play_handoff/shawarma58-v1.0.0"


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_output_path(path: Path) -> None:
    resolved = path.resolve()
    allowed = (ROOT / "build").resolve()
    if allowed != resolved and allowed not in resolved.parents:
        raise SystemExit(f"Refusing to write outside build/: {path}")


def load_manifest(handoff: Path) -> dict[str, object]:
    manifest_path = handoff / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing handoff manifest: {relative(manifest_path)}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def archive_path_for(handoff: Path) -> Path:
    return handoff.parent / f"{handoff.name}.zip"


def write_archive(handoff: Path, archive: Path) -> dict[str, object]:
    manifest = load_manifest(handoff)
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise SystemExit("handoff manifest.files must be an object")

    archive_files = sorted(set(files.keys()) | {"manifest.json"})
    missing_on_disk = sorted(relative_name for relative_name in archive_files if not (handoff / relative_name).is_file())
    if missing_on_disk:
        raise SystemExit(f"Handoff file set mismatch; missing={missing_on_disk}")

    if archive.exists():
        archive.unlink()
    ensure_output_path(archive)
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for relative_name in archive_files:
            zf.write(handoff / relative_name, arcname=f"{handoff.name}/{relative_name}")

    sidecar = archive.with_suffix(archive.suffix + ".sha256")
    sidecar.write_text(f"{sha256(archive)}  {archive.name}\n", encoding="utf-8")

    report = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "handoff": relative(handoff),
        "archive": relative(archive),
        "sha256File": relative(sidecar),
        "bytes": archive.stat().st_size,
        "sha256": sha256(archive),
        "manifestSha256": sha256(handoff / "manifest.json"),
        "fileCount": len(archive_files),
        "manifestFileCount": len(files),
        "archiveInput": "manifest.files plus manifest.json",
    }
    report_path = archive.with_suffix(archive.suffix + ".json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF), help="handoff directory")
    parser.add_argument("--archive", default="", help="optional archive path under build/")
    args = parser.parse_args()

    handoff = Path(args.handoff)
    if not handoff.is_absolute():
        handoff = ROOT / handoff
    if not handoff.is_dir():
        raise SystemExit(f"Missing handoff directory: {relative(handoff)}")

    archive = Path(args.archive) if args.archive else archive_path_for(handoff)
    if not archive.is_absolute():
        archive = ROOT / archive
    report = write_archive(handoff, archive)
    print(f"Play handoff archive: {report['archive']}")
    print(f"Files archived: {report['fileCount']}")
    print(f"Size: {report['bytes']} bytes")
    print(f"SHA-256: {report['sha256']}")


if __name__ == "__main__":
    main()
