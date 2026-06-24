import asyncio
import io
from typing import Optional

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QThread, Signal
from PySide6.QtGui import QImage

from PIL import Image, ImageFilter, ImageOps

try:
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

    _OCR_AVAILABLE = True
except Exception:
    _OCR_AVAILABLE = False


TARGET_HEIGHT_PX = 1600
MAX_UPSCALE = 4.0


def is_available() -> bool:
    return _OCR_AVAILABLE


def _qimage_to_pil(image: QImage) -> Image.Image:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    image.save(buf, "PNG")
    buf.close()
    return Image.open(io.BytesIO(bytes(ba))).convert("RGB")


def _preprocess_png(image: QImage) -> bytes:
    pil = _qimage_to_pil(image)
    w, h = pil.size

    if h < TARGET_HEIGHT_PX:
        scale = min(MAX_UPSCALE, TARGET_HEIGHT_PX / max(h, 1))
        if scale > 1.05:
            pil = pil.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    gray = pil.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=1.2, percent=140, threshold=2))

    out = io.BytesIO()
    gray.convert("RGB").save(out, format="PNG")
    return out.getvalue()


async def _ocr_async(png_bytes: bytes) -> str:
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream.get_output_stream_at(0))
    writer.write_bytes(png_bytes)
    await writer.store_async()
    writer.detach_stream()

    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()

    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        return ""
    result = await engine.recognize_async(bitmap)
    return result.text or ""


class OcrWorker(QThread):
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, image: QImage, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._image = image

    def run(self) -> None:
        if not _OCR_AVAILABLE:
            self.failed.emit("Windows OCR을 사용할 수 없습니다")
            return
        try:
            png_bytes = _preprocess_png(self._image)
        except Exception as exc:
            self.failed.emit(f"이미지 인코딩 실패: {exc}")
            return
        # 빠른 연속 OCR 등으로 이미 폐기 요청된 워커라면 OCR을 시작하지 않는다.
        # (app._detach_ocr_worker 의 requestInterruption/quit/wait 과 협조)
        if self.isInterruptionRequested():
            return
        try:
            loop = asyncio.new_event_loop()
            try:
                text = loop.run_until_complete(_ocr_async(png_bytes))
            finally:
                loop.close()
        except Exception as exc:
            self.failed.emit(f"OCR 실패: {exc}")
            return
        self.finished_ok.emit(text.strip())
