# Copyright 2026 ICKAB. All rights reserved.
"""Printer-neutral image pipeline for ICKAB Label Studio.

The designer stores *references* to Odoo images, never printer commands or huge
base64 payloads.  This service owns the complete conversion boundary:

    Odoo Binary/Image value -> validated raster -> fitted RGBA -> thermal mono
    -> packed 1-bit bitmap + PNG preview

Keeping the pipeline in one service avoids having decoding rules duplicated in
renderers and makes malformed image data fail with deterministic diagnostics.
"""

import base64
import binascii
import io
import re
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from odoo import _, models
from odoo.exceptions import UserError


MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_SOURCE_PIXELS = 40_000_000
MAX_NESTED_BASE64_DEPTH = 2

_BIN_SIZE_RE = re.compile(
    r"^\s*\d+(?:[.,]\d+)?\s*(?:bytes?|[kmgt]i?b)\s*$",
    re.IGNORECASE,
)
_BASE64_TEXT_RE = re.compile(rb"^[A-Za-z0-9+/=_\-\s]+$")
_SVG_PREFIX_RE = re.compile(
    r"^\s*(?:<\?xml[^>]*>\s*)?(?:<!--.*?-->\s*)*(?:<!doctype\s+svg.*?>\s*)?<svg\b",
    re.IGNORECASE | re.DOTALL,
)


class IckabLabelImageProcessor(models.AbstractModel):
    _name = "ickab.label.image.processor"
    _description = "ICKAB Label Studio Image Processor"

    @staticmethod
    def _is_bin_size_placeholder(value):
        if isinstance(value, bytes):
            try:
                value = value.decode("ascii")
            except UnicodeDecodeError:
                return False
        return isinstance(value, str) and bool(_BIN_SIZE_RE.fullmatch(value.strip()))

    @staticmethod
    def _looks_like_raster_signature(raw):
        if not raw:
            return False
        return bool(
            raw.startswith(b"\x89PNG\r\n\x1a\n")
            or raw.startswith(b"\xff\xd8\xff")
            or raw.startswith((b"GIF87a", b"GIF89a"))
            or raw.startswith(b"BM")
            or raw.startswith((b"II*\x00", b"MM\x00*"))
            or (len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP")
        )

    @staticmethod
    def _is_webp(raw):
        return bool(
            raw
            and len(raw) >= 16
            and raw.startswith(b"RIFF")
            and raw[8:12] == b"WEBP"
            and raw[12:16] in {b"VP8 ", b"VP8L", b"VP8X"}
        )

    @staticmethod
    def _is_svg(raw):
        if not raw:
            return False
        try:
            head = raw[:8192].decode("utf-8-sig", errors="ignore")
        except Exception:
            return False
        return bool(_SVG_PREFIX_RE.search(head))

    @staticmethod
    def _strip_data_uri(text):
        text = str(text or "").strip()
        if not text.lower().startswith("data:"):
            return text, False
        if "," not in text:
            raise UserError(_("La imagen contiene un Data URI incompleto."))
        header, payload = text.split(",", 1)
        if not header.lower().startswith("data:image/"):
            raise UserError(_("El Data URI recibido no corresponde a una imagen."))
        if ";base64" not in header.lower():
            raise UserError(_("Label Studio sólo admite Data URI de imagen codificados en Base64."))
        return payload, True

    @staticmethod
    def _repair_padding(encoded):
        return encoded + b"=" * ((4 - len(encoded) % 4) % 4)

    @classmethod
    def _decode_base64_text(cls, encoded):
        encoded = re.sub(rb"\s+", b"", encoded or b"")
        if not encoded:
            return b""
        # Odoo uses standard Base64, but accepting URL-safe alphabet makes the
        # pipeline resilient to values coming from custom image fields/widgets.
        normalized = encoded.replace(b"-", b"+").replace(b"_", b"/")
        normalized = cls._repair_padding(normalized)
        try:
            return base64.b64decode(normalized, validate=True)
        except (binascii.Error, ValueError, TypeError):
            return b""

    @classmethod
    def _raw_from_value(cls, value, image_label="imagen"):
        """Return decoded bytes from an Odoo Binary/Image value.

        Accepted inputs: raw raster bytes, Odoo Base64 bytes/str, and browser
        ``data:image/...;base64`` strings.  Human-readable ``bin_size`` values
        are rejected explicitly instead of being mistaken for Base64.
        """
        if value in (False, None, "", b""):
            return b""
        if cls._is_bin_size_placeholder(value):
            raise UserError(_(
                "La imagen '%(image)s' fue recibida sólo como tamaño de archivo. "
                "Label Studio necesita el contenido binario real.",
                image=image_label,
            ))

        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytearray):
            value = bytes(value)

        # Raw binary image: avoid trying to decode arbitrary binary as text.
        if isinstance(value, bytes):
            raw_value = value.strip()
            if cls._looks_like_raster_signature(raw_value) or cls._is_svg(raw_value):
                return raw_value
            # PNG/JPEG/GIF/BMP/TIFF/WEBP and other raster formats are validated
            # by Pillow later; here only decide whether this is textual Base64.
            try:
                text = raw_value.decode("ascii")
            except UnicodeDecodeError:
                raw = raw_value
            else:
                if cls._is_bin_size_placeholder(text):
                    raise UserError(_(
                        "La imagen '%(image)s' fue recibida sólo como tamaño de archivo.",
                        image=image_label,
                    ))
                text, _is_data_uri = cls._strip_data_uri(text)
                encoded = text.encode("ascii", errors="strict")
                raw = cls._decode_base64_text(encoded)
                # If the ASCII bytes were not valid Base64, they may still be a
                # rare textual image (SVG).  Everything else is malformed.
                if not raw:
                    if cls._is_svg(raw_value):
                        raw = raw_value
                    else:
                        raise UserError(_(
                            "La imagen '%(image)s' no contiene Base64 válido ni datos gráficos reconocibles.",
                            image=image_label,
                        ))
        elif isinstance(value, str):
            text, _is_data_uri = cls._strip_data_uri(value)
            if cls._is_bin_size_placeholder(text):
                raise UserError(_(
                    "La imagen '%(image)s' fue recibida sólo como tamaño de archivo.",
                    image=image_label,
                ))
            try:
                encoded = text.encode("ascii", errors="strict")
            except UnicodeEncodeError as exc:
                raise UserError(_(
                    "La imagen '%(image)s' no contiene Base64 ASCII válido.",
                    image=image_label,
                )) from exc
            raw = cls._decode_base64_text(encoded)
            if not raw:
                raise UserError(_(
                    "La imagen '%(image)s' no contiene Base64 válido.",
                    image=image_label,
                ))
        else:
            raise UserError(_(
                "La imagen '%(image)s' usa un tipo de dato no soportado: %(data_type)s.",
                image=image_label,
                data_type=type(value).__name__,
            ))

        if len(raw) > MAX_IMAGE_BYTES:
            raise UserError(_(
                "La imagen '%(image)s' supera el límite de %(limit)s MB permitido por Label Studio.",
                image=image_label,
                limit=MAX_IMAGE_BYTES // (1024 * 1024),
            ))
        return raw

    @classmethod
    def _try_unwrap_nested_base64(cls, raw):
        """Recover one/two accidental Base64 wrappers without accepting junk."""
        current = raw
        for _depth in range(MAX_NESTED_BASE64_DEPTH):
            if not current or cls._is_svg(current):
                return current
            candidate = current.strip()
            if len(candidate) < 16 or not _BASE64_TEXT_RE.fullmatch(candidate):
                return current
            decoded = cls._decode_base64_text(candidate)
            if not decoded or decoded == current or len(decoded) > MAX_IMAGE_BYTES:
                return current
            # Only unwrap when the decoded payload is clearly binary-ish or SVG.
            if cls._is_svg(decoded) or any(byte > 0x7F or byte == 0 for byte in decoded[:128]):
                current = decoded
                continue
            # It may still be an ASCII-encoded PNG/JPEG wrapper; let Pillow
            # decide below, but avoid recursively consuming normal text.
            current = decoded
        return current

    def normalize_base64(self, value, image_label="imagen"):
        """Compatibility helper returning canonical standard Base64.

        A ``bin_size`` placeholder returns an empty string for compatibility with
        older Studio callers.  The real rendering path uses ``prepare_bitmap``
        directly and raises a precise diagnostic instead of silently continuing.
        """
        cls = type(self)
        if value in (False, None, "", b"") or cls._is_bin_size_placeholder(value):
            return ""
        raw = cls._raw_from_value(value, image_label=image_label)
        raw = cls._try_unwrap_nested_base64(raw)
        if not raw:
            return ""
        return base64.b64encode(raw).decode("ascii")

    @staticmethod
    def _decode_webp_isolated(raw, image_label):
        """Decode WebP without changing Pillow's global plugin registry.

        Odoo intentionally calls ``Image.preinit()`` and then sets
        ``Image._initialized = 2`` in ``odoo.tools.image``.  As a result, the
        generic ``Image.open`` path inside a running Odoo worker only sees the
        small preloaded format set and does not register WebP even when the
        Pillow build has libwebp support.

        Resetting that global flag or importing ``WebPImagePlugin`` would alter
        Odoo's process-wide image policy.  Label Studio therefore uses Pillow's
        already-installed libwebp backend directly and converts only the first
        frame to a normal in-memory Pillow image.
        """
        try:
            from PIL import _webp
        except ImportError as exc:
            raise UserError(_(
                "La imagen '%(image)s' está en formato WebP, pero el servidor no tiene "
                "el decodificador WebP de Pillow disponible.",
                image=image_label,
            )) from exc

        decoder_cls = getattr(_webp, "WebPAnimDecoder", None)
        if decoder_cls is None:
            raise UserError(_(
                "La imagen '%(image)s' está en formato WebP, pero la instalación de "
                "Pillow no dispone de WebPAnimDecoder.",
                image=image_label,
            ))

        try:
            decoder = decoder_cls(raw)
            info = decoder.get_info()

            # Pillow 10.x returns:
            #   (width, height, loop, bgcolor, frames, rawmode)
            # Newer Pillow returns:
            #   ((width, height), loop, bgcolor, frames, rawmode)
            if len(info) == 6 and isinstance(info[0], int):
                width, height, _loop, _bgcolor, frame_count, rawmode = info
            elif len(info) == 5 and isinstance(info[0], (tuple, list)) and len(info[0]) == 2:
                (width, height), _loop, _bgcolor, frame_count, rawmode = info
            else:
                raise ValueError("WebP decoder returned an unsupported info structure")

            width = int(width)
            height = int(height)
            frame_count = int(frame_count or 0)
            rawmode = str(rawmode or "")

            if width <= 0 or height <= 0 or frame_count < 1:
                raise ValueError("WebP decoder returned invalid dimensions or no frames")
            if width * height > MAX_SOURCE_PIXELS:
                raise UserError(_(
                    "La imagen '%(image)s' es demasiado grande (%(width)s×%(height)s px).",
                    image=image_label,
                    width=width,
                    height=height,
                ))
            if rawmode not in {"RGB", "RGBX", "RGBA"}:
                raise ValueError(f"unsupported WebP raw mode: {rawmode}")

            frame = decoder.get_next()
            if not frame or not isinstance(frame, tuple) or not frame[0]:
                raise ValueError("WebP decoder could not return the first frame")
            pixels = frame[0]

            bytes_per_pixel = {"RGB": 3, "RGBX": 4, "RGBA": 4}[rawmode]
            expected = width * height * bytes_per_pixel
            if len(pixels) != expected:
                raise ValueError(
                    f"WebP frame size mismatch: got {len(pixels)} bytes, expected {expected}"
                )

            target_mode = "RGBA" if rawmode == "RGBA" else "RGB"
            image = Image.frombytes(
                target_mode,
                (width, height),
                pixels,
                "raw",
                rawmode,
            )

            # Preserve EXIF only long enough to honor orientation.  Label Studio
            # emits a thermal bitmap, so ICC/XMP/EXIF metadata itself is not
            # propagated to the output.
            try:
                exif = decoder.get_chunk("EXIF")
            except Exception:
                exif = None
            if exif:
                image.info["exif"] = exif

            image = ImageOps.exif_transpose(image).convert("RGBA")
            return image, "WEBP"
        except UserError:
            raise
        except Exception as exc:
            raise UserError(_(
                "La imagen '%(image)s' es WebP, pero no pudo decodificarse con el "
                "backend WebP aislado de Label Studio. Detalle técnico: %(detail)s",
                image=image_label,
                detail=str(exc),
            )) from exc

    @staticmethod
    def _open_verified_raster(raw, image_label):
        if IckabLabelImageProcessor._is_svg(raw):
            raise UserError(_(
                "La imagen '%(image)s' está en formato SVG. "
                "Para impresión térmica conviértala a PNG o JPG/JPEG.",
                image=image_label,
            ))
        if raw.startswith(b"%PDF-"):
            raise UserError(_(
                "La imagen '%(image)s' es un PDF. Use una imagen PNG o JPG/JPEG.",
                image=image_label,
            ))

        # WebP is deliberately not part of Odoo's globally registered Pillow
        # plugins. Decode it locally without modifying Image._initialized or
        # Image.OPEN for the rest of the Odoo worker.
        if IckabLabelImageProcessor._is_webp(raw):
            return IckabLabelImageProcessor._decode_webp_isolated(raw, image_label)

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                probe = Image.open(io.BytesIO(raw))
                image_format = (probe.format or "").upper() or "DESCONOCIDO"
                width, height = probe.size
                if width <= 0 or height <= 0:
                    raise UserError(_("La imagen '%(image)s' no tiene dimensiones válidas.", image=image_label))
                if width * height > MAX_SOURCE_PIXELS:
                    raise UserError(_(
                        "La imagen '%(image)s' es demasiado grande (%(width)s×%(height)s px).",
                        image=image_label,
                        width=width,
                        height=height,
                    ))
                probe.verify()

                image = Image.open(io.BytesIO(raw))
                image.load()
                image = ImageOps.exif_transpose(image).convert("RGBA")
                return image, image_format
        except UserError:
            raise
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise UserError(_(
                "La imagen '%(image)s' no es un archivo gráfico raster soportado por Label Studio. "
                "Se recibieron %(bytes)s bytes.",
                image=image_label,
                bytes=len(raw),
            )) from exc
        except Image.DecompressionBombError as exc:
            raise UserError(_(
                "La imagen '%(image)s' excede el límite seguro de resolución.",
                image=image_label,
            )) from exc
        except Image.DecompressionBombWarning as exc:
            raise UserError(_(
                "La imagen '%(image)s' tiene una resolución excesiva para procesarse de forma segura.",
                image=image_label,
            )) from exc
        except Exception as exc:
            raise UserError(_(
                "La imagen '%(image)s' no puede ser procesada. Detalle técnico: %(detail)s",
                image=image_label,
                detail=str(exc),
            )) from exc

    def prepare_bitmap(self, value, width_dot, height_dot, options=None, image_label="imagen"):
        """Return printer-neutral 1-bit bitmap plus thermal preview metadata."""
        cls = type(self)
        if value in (False, None, "", b""):
            return {}
        options = options or {}
        raw = cls._raw_from_value(value, image_label=image_label)
        raw = cls._try_unwrap_nested_base64(raw)
        image, image_format = cls._open_verified_raster(raw, image_label=image_label)

        width_dot = max(1, int(width_dot or 1))
        height_dot = max(1, int(height_dot or 1))
        target = (width_dot, height_dot)
        fit = str(options.get("fit") or "contain")
        resampling = getattr(Image, "Resampling", Image).LANCZOS

        if fit == "stretch":
            canvas = image.resize(target, resampling)
        elif fit == "cover":
            canvas = ImageOps.fit(image, target, method=resampling, centering=(0.5, 0.5))
        else:
            fitted = ImageOps.contain(image, target, method=resampling)
            canvas = Image.new("RGBA", target, (255, 255, 255, 255))
            x = (width_dot - fitted.width) // 2
            y = (height_dot - fitted.height) // 2
            canvas.alpha_composite(fitted, (x, y))

        # Flatten transparency over white exactly once, then convert to luminance.
        background = Image.new("RGBA", target, (255, 255, 255, 255))
        background.alpha_composite(canvas)
        gray = background.convert("RGB").convert("L")
        if bool(options.get("invert")):
            gray = ImageOps.invert(gray)

        threshold_value = options.get("threshold", 128)
        if threshold_value in (None, ""):
            threshold_value = 128
        threshold = max(0, min(255, int(threshold_value)))
        dither = str(options.get("dither") or "none")
        if dither == "floyd_steinberg":
            dither_mode = Image.Dither.FLOYDSTEINBERG if hasattr(Image, "Dither") else Image.FLOYDSTEINBERG
            mono = gray.convert("1", dither=dither_mode)
        else:
            mono = gray.point(lambda pixel: 0 if pixel <= threshold else 255, mode="1")

        bytes_per_row = (width_dot + 7) // 8
        packed = bytearray(bytes_per_row * height_dot)
        pixels = mono.load()
        for y in range(height_dot):
            row_offset = y * bytes_per_row
            for x in range(width_dot):
                if pixels[x, y] == 0:  # black pixel -> printer bit 1
                    packed[row_offset + (x // 8)] |= 0x80 >> (x % 8)

        preview_buffer = io.BytesIO()
        mono.convert("L").save(preview_buffer, format="PNG", optimize=True)
        preview_b64 = base64.b64encode(preview_buffer.getvalue()).decode("ascii")
        return {
            "image_bitmap_b64": base64.b64encode(bytes(packed)).decode("ascii"),
            "image_bytes_per_row": bytes_per_row,
            "image_width_dot": width_dot,
            "image_height_dot": height_dot,
            "image_preview_src": f"data:image/png;base64,{preview_b64}",
            "image_format": image_format,
            "image_source_bytes": len(raw),
        }
