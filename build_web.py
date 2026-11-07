"""Empaqueta el motor Python y sincroniza la portada para alojamiento estático."""

from pathlib import Path
import shutil
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent


def build_web():
    web = ROOT / "web"
    with ZipFile(web / "aero_gnc.zip", "w", compression=ZIP_DEFLATED) as bundle:
        for source in sorted((ROOT / "src" / "aero_gnc").rglob("*.py")):
            entry = ZipInfo(source.relative_to(ROOT / "src").as_posix())
            bundle.writestr(entry, source.read_bytes(), compress_type=ZIP_DEFLATED)
    for name in ("index.html", "styles.css", "app.js", "engine.js", "engine-worker.js", "aero_gnc.zip"):
        shutil.copy2(web / name, ROOT / name)
    shutil.copytree(web / "data", ROOT / "data", dirs_exist_ok=True)
    print("Panel web preparado en web/ y en la raíz del proyecto.")


if __name__ == "__main__":
    build_web()
