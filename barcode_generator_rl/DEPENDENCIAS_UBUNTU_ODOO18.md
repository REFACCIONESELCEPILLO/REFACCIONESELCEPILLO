# Dependencias — Product Barcode Generator RL / ICKAB

## Python — instalar dentro del venv de Odoo

```bash
VENV="/ruta/al/venv"
$VENV/bin/pip install "Pillow==10.2.0" "python-barcode==0.16.1" "treepoem==3.27.1"
```

## Sistema operativo — Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y ghostscript
gs --version
```

## Verificación Python

```bash
$VENV/bin/python - <<'PY'
import barcode
import treepoem
from PIL import Image
print("python-barcode OK")
print("Pillow OK")
print("treepoem OK")
PY
```

Ghostscript es una dependencia de sistema y no debe instalarse mediante pip ni ejecutarse con sudo desde Odoo.
