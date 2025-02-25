from .imports import *

class Locale:
    language: str = "en"
    texts: Dict[str, Dict[str, str]] = {}

    @classmethod
    def set_language(cls, language: str) -> None:
        cls.language = language

    @classmethod
    def get_text(cls, text_id: str) -> str:
        if text_id in cls.texts and cls.language in cls.texts[text_id]:
            return cls.texts[text_id][cls.language]
        return text_id

    @classmethod
    def load_from_csv(cls, file_path: str) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                for row in reader:
                    text_id, *translations = row
                    cls.texts[text_id] = dict(zip(header[1:], translations))
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
        except Exception as e:
            print(f"Error loading CSV file: {e}")