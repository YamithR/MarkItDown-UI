from pathlib import Path
from typing import List, Optional

from .ocr_backends import OCRBackend, EasyOCRBackend, TesseractBackend, BuiltinBackend

EASYOCR_LANG_MAP = {"en": "en", "es": "es", "eng": "en", "spa": "es"}
TESSERACT_LANG_MAP = {"en": "eng", "es": "spa", "eng": "eng", "spa": "spa"}


class OCRManager:
    def __init__(self, engine, config=None):
        self.engine = engine
        self.config = config or {}
        self._backends: List[OCRBackend] = []
        self._active: Optional[OCRBackend] = None
        self._available_cache: Optional[List[OCRBackend]] = None
        self._init_backends()

    def _get_raw_langs(self) -> List[str]:
        raw = self.config.get('ocr_languages') or ['en']
        return [str(l).strip().lower() for l in raw if str(l).strip()]

    def _easyocr_langs(self) -> tuple:
        mapped = []
        for l in self._get_raw_langs():
            m = EASYOCR_LANG_MAP.get(l, l)
            if m not in mapped:
                mapped.append(m)
        return tuple(mapped) or ('en',)

    def _tesseract_lang(self) -> str:
        for l in self._get_raw_langs():
            m = TESSERACT_LANG_MAP.get(l, l)
            if m:
                return m
        return 'eng'

    def _init_backends(self):
        gpu = self.config.get('ocr_gpu', False)
        model_dir = self.config.get('easyocr_model_dir')
        tesseract_cmd = self.config.get('tesseract_cmd')

        easyocr_kwargs = dict(
            languages=self._easyocr_langs(),
            gpu=gpu,
        )
        if model_dir:
            easyocr_kwargs['model_storage_directory'] = model_dir
            easyocr_kwargs['download_enabled'] = False

        self._backends = [
            EasyOCRBackend(**easyocr_kwargs),
            TesseractBackend(lang=self._tesseract_lang(), tesseract_cmd=tesseract_cmd),
            BuiltinBackend(self.engine),
        ]

    def auto_select_best(self) -> Optional[OCRBackend]:
        available = self.get_available()
        if not available:
            self._active = None
            return None
        available.sort(key=lambda b: b.priority(), reverse=True)
        self._active = available[0]
        return self._active

    def select_without_easyocr(self) -> Optional[OCRBackend]:
        available = [b for b in self.get_available()
                     if not isinstance(b, EasyOCRBackend)]
        if not available:
            self._active = None
            return None
        available.sort(key=lambda b: b.priority(), reverse=True)
        self._active = available[0]
        return self._active

    def get_available(self) -> List[OCRBackend]:
        if self._available_cache is None:
            self._available_cache = [b for b in self._backends if b.is_available()]
        return list(self._available_cache)

    def warm_up(self) -> bool:
        for b in self._backends:
            if isinstance(b, EasyOCRBackend):
                return b.warm()
        return False

    def get_all_names(self) -> List[str]:
        return [b.get_name() for b in self._backends]

    def set_active(self, backend_name: str) -> Optional[OCRBackend]:
        for b in self.get_available():
            if b.get_name() == backend_name:
                self._active = b
                return b
        self._active = self.get_available()[0] if self.get_available() else None
        return self._active

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