from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import fitz


class OCRBackend(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def extract_text(self, image_path: Path) -> str:
        pass

    def priority(self) -> int:
        return 0

    def extract_from_pdf(self, pdf_path: Path, page_num: int) -> str:
        doc = fitz.open(pdf_path)
        try:
            page = doc[page_num]
            pix = page.get_pixmap(dpi=300)
            img_path = pdf_path.with_suffix(f".page{page_num}.png")
            pix.save(str(img_path))
            try:
                return self.extract_text(img_path)
            finally:
                img_path.unlink(missing_ok=True)
        finally:
            doc.close()


class EasyOCRBackend(OCRBackend):
    def __init__(self, languages=('en',), gpu=False,
                 model_storage_directory=None, download_enabled=True):
        self._reader = None
        self._languages = languages
        self._gpu = gpu
        self._model_dir = model_storage_directory
        self._download_enabled = download_enabled

    def _get_reader(self):
        if self._reader is None:
            import easyocr
            kwargs = {'gpu': self._gpu}
            if self._model_dir:
                kwargs['model_storage_directory'] = self._model_dir
                kwargs['download_enabled'] = self._download_enabled
            self._reader = easyocr.Reader(list(self._languages), **kwargs)
        return self._reader

    def is_available(self) -> bool:
        try:
            import easyocr
        except ImportError:
            return False
        if self._model_dir:
            from pathlib import Path
            md = Path(self._model_dir)
            if not md.is_dir():
                return False
            has_model = any(md.rglob("*.pth")) or any(md.rglob("*.onnx")) \
                or any(md.rglob("*.yaml")) or any(md.rglob("*.json"))
            if not has_model:
                return False
        return True

    def get_name(self) -> str:
        return f"EasyOCR ({', '.join(self._languages)})"

    def priority(self) -> int:
        return 30

    def extract_text(self, image_path: Path) -> str:
        reader = self._get_reader()
        result = reader.readtext(str(image_path), detail=0, paragraph=True)
        return '\n\n'.join(result)


class TesseractBackend(OCRBackend):
    def __init__(self, lang='eng', tesseract_cmd=None):
        self._lang = lang
        self._cmd = tesseract_cmd

    def is_available(self) -> bool:
        try:
            import pytesseract
            if self._cmd:
                pytesseract.pytesseract.tesseract_cmd = self._cmd
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def get_name(self) -> str:
        return f"Tesseract ({self._lang})"

    def priority(self) -> int:
        return 20

    def extract_text(self, image_path: Path) -> str:
        import pytesseract
        from PIL import Image
        if self._cmd:
            pytesseract.pytesseract.tesseract_cmd = self._cmd
        return pytesseract.image_to_string(Image.open(image_path), lang=self._lang)


class BuiltinBackend(OCRBackend):
    def __init__(self, engine):
        self._engine = engine

    def is_available(self) -> bool:
        return True

    def get_name(self) -> str:
        return "MarkItDown Built-in"

    def priority(self) -> int:
        return 10

    def extract_text(self, image_path: Path) -> str:
        result = self._engine.convert(str(image_path))
        return result.markdown


def predownload_easyocr_models(languages=('en',), output_dir='models'):
    import easyocr
    reader = easyocr.Reader(list(languages), gpu=False,
                            model_storage_directory=output_dir,
                            download_enabled=True)
    return output_dir