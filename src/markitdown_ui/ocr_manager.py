from pathlib import Path
from typing import Optional, List
from .ocr_backends import OCRBackend, EasyOCRBackend, TesseractBackend, BuiltinBackend


class OCRManager:
    def __init__(self, engine, config=None):
        self.engine = engine
        self.config = config or {}
        self._backends: List[OCRBackend] = []
        self._active: Optional[OCRBackend] = None
        self._init_backends()

    def _init_backends(self):
        languages = tuple(self.config.get('ocr_languages', ['en']))
        gpu = self.config.get('ocr_gpu', False)
        tesseract_lang = self.config.get('tesseract_lang', 'eng')
        tesseract_cmd = self.config.get('tesseract_cmd')

        self._backends = [
            EasyOCRBackend(languages=languages, gpu=gpu),
            TesseractBackend(lang=tesseract_lang, tesseract_cmd=tesseract_cmd),
            BuiltinBackend(self.engine),
        ]

    def get_available(self) -> List[OCRBackend]:
        return [b for b in self._backends if b.is_available()]

    def get_all_names(self) -> List[str]:
        return [b.get_name() for b in self._backends]

    def set_active(self, backend_name: str):
        for b in self.get_available():
            if b.get_name() == backend_name:
                self._active = b
                return
        self._active = self.get_available()[0] if self.get_available() else None

    def get_active(self) -> Optional[OCRBackend]:
        if self._active is None:
            self._active = self.get_available()[0] if self.get_available() else None
        return self._active

    def extract_image_text(self, image_path: Path) -> str:
        backend = self.get_active()
        if backend:
            return backend.extract_text(image_path)
        return ""

    def extract_pdf_page_text(self, pdf_path: Path, page_num: int) -> str:
        backend = self.get_active()
        if backend:
            return backend.extract_from_pdf(pdf_path, page_num)
        return ""