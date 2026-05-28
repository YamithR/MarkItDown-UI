#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PACKAGE="markitdown-gui"
VERSION="1.0.0"
ARCH="all"
BUILD_ROOT="$(mktemp -d)"
DEB_DIR="$BUILD_ROOT/${PACKAGE}_${VERSION}_${ARCH}"

echo "==> Creando estructura del paquete..."
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/usr/bin"
mkdir -p "$DEB_DIR/usr/lib/markitdown-gui"
mkdir -p "$DEB_DIR/usr/share/applications"
mkdir -p "$DEB_DIR/usr/share/pixmaps"

echo "==> Generando icono..."
python3 -c "
from PIL import Image, ImageDraw, ImageFont

size = 128
img = Image.new('RGBA', (size, size), (30, 100, 200, 255))
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 72)
except (IOError, OSError):
    font = ImageFont.load_default()
bbox = draw.textbbox((0, 0), 'M', font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
tx = (size - tw) // 2
ty = (size - th) // 2 - 4
draw.text((tx, ty), 'M', fill='white', font=font)
img.save('$DEB_DIR/usr/share/pixmaps/markitdown-gui.png')
"

echo "==> Copiando gui.py..."
cp src/markitdown_ui/gui.py "$DEB_DIR/usr/lib/markitdown-gui/gui.py"

echo "==> Creando wrapper /usr/bin/markitdown-gui..."
cat > "$DEB_DIR/usr/bin/markitdown-gui" << 'WRAPPER'
#!/bin/sh
exec python3 /usr/lib/markitdown-gui/gui.py "$@"
WRAPPER
chmod +x "$DEB_DIR/usr/bin/markitdown-gui"

echo "==> Creando archivo .desktop..."
cat > "$DEB_DIR/usr/share/applications/markitdown-gui.desktop" << DESKTOP
[Desktop Entry]
Name=MarkItDown Converter
Comment=Convierte varios formatos de archivo a Markdown
Exec=markitdown-gui
Icon=markitdown-gui
Terminal=false
Type=Application
Categories=Utility;Office;
StartupNotify=true
DESKTOP

echo "==> Creando archivo DEBIAN/control..."
cat > "$DEB_DIR/DEBIAN/control" << CONTROL
Package: markitdown-gui
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Depends: python3 (>= 3.10), python3-tk, python3-pip
Maintainer: Yamith R. <yamith@example.com>
Description: Interfaz grafica para MarkItDown
 Convierte archivos PDF, DOCX, PPTX, XLSX, HTML,
 imagenes, audio, EPUB, CSV, y muchos otros formatos
 a Markdown con un solo clic.
 .
 Dependencias de Python se instalan automaticamente
 via pip en la primera ejecucion.
CONTROL

echo "==> Creando archivo DEBIAN/postinst..."
cat > "$DEB_DIR/DEBIAN/postinst" << 'POSTINST'
#!/bin/sh
set -e

case "$1" in
    configure)
        echo "markitdown-gui: Instalando dependencias de Python..."
        PIP_CMD="/usr/bin/pip3 install \"markitdown[all]\" --break-system-packages"
        if eval "$PIP_CMD" 2>&1; then
            echo "markitdown-gui: Dependencias instaladas correctamente."
        else
            echo "markitdown-gui: Advertencia - no se pudieron instalar las dependencias automaticamente."
            echo "markitdown-gui: Ejecuta manualmente: $PIP_CMD"
        fi
        ;;
esac
POSTINST
chmod +x "$DEB_DIR/DEBIAN/postinst"

echo "==> Construyendo .deb..."
dpkg-deb --build "$DEB_DIR" > /dev/null
mv "${BUILD_ROOT}/${PACKAGE}_${VERSION}_${ARCH}.deb" ./dist/

rm -rf "$BUILD_ROOT"

echo ""
echo "============================================"
echo "  Paquete creado: dist/${PACKAGE}_${VERSION}_${ARCH}.deb"
echo "============================================"
echo ""
echo "Para instalarlo:"
echo "  sudo dpkg -i dist/${PACKAGE}_${VERSION}_${ARCH}.deb"
echo "  sudo apt-get install -f"
echo ""
