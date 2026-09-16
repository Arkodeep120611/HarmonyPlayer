from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_package():
    base_dir = Path(__file__).resolve().parent
    package_dir = base_dir / "app"
    spec = importlib.util.spec_from_file_location(
        "harmonyplayer_package",
        package_dir / "__init__.py",
        submodule_search_locations=[str(package_dir)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load HarmonyPlayer package.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


package = _load_package()
app = getattr(package, "app", package.create_app())


if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
