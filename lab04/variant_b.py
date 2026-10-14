"""Файловый менеджер с дескрипторами, миксинами и контекстом."""

import os
from pathlib import Path


class ValidatedFilename:
    """Разрешает путь к файлу без недопустимых для Windows символов."""

    def __set_name__(self, owner, name):
        self.storage_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.storage_name)

    def __set__(self, obj, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("имя файла должно быть непустой строкой")
        path = Path(value)
        if any(char in '<>"|?*' or ord(char) < 32 for char in value):
            raise ValueError("имя файла содержит недопустимые символы")
        drive = path.drive if path.is_absolute() else ""
        if ":" in value[len(drive):]:
            raise ValueError("двоеточие допустимо только в обозначении диска")
        setattr(obj, self.storage_name, value)


class ValidatedMode:
    """Ограничивает режимы текстовыми r, w, a и их вариантами с +."""

    ALLOWED_MODES = {"r", "w", "a", "r+", "w+", "a+"}

    def __set_name__(self, owner, name):
        self.storage_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.storage_name)

    def __set__(self, obj, value):
        if value not in self.ALLOWED_MODES:
            raise ValueError(f"недопустимый режим доступа: {value!r}")
        setattr(obj, self.storage_name, value)


class FileManager:
    """Открывает и гарантированно закрывает текстовый файл."""

    filename = ValidatedFilename()
    mode = ValidatedMode()

    def __init__(self, filename: str, mode: str = "r"):
        self.filename = filename
        self.mode = mode
        self._file = None

    def __enter__(self):
        if self._file is not None:
            raise RuntimeError("файл уже открыт")
        self._file = open(self.filename, self.mode, encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file is not None:
            self._file.close()
            self._file = None
        return False

    def _require_open(self):
        if self._file is None:
            raise RuntimeError("файл нужно открыть через with")
        return self._file

    def read(self) -> str:
        return self._require_open().read()

    def write(self, data: str) -> None:
        if not isinstance(data, str):
            raise TypeError("для текстового файла нужна строка")
        self._require_open().write(data)


class LogManager:
    """Миксин для записи факта операции в стандартный вывод."""

    def log_operation(self, operation: str) -> None:
        print(f"[{type(self).__name__}] {operation}: {self.filename}")


class SecureManager:
    """Миксин предварительной проверки доступа к существующему пути."""

    def check_permissions(self) -> bool:
        path = Path(self.filename)
        read_mode = self.mode.startswith("r") or "+" in self.mode
        write_mode = self.mode[0] in "wa" or "+" in self.mode
        if path.exists():
            return ((not read_mode or os.access(path, os.R_OK))
                    and (not write_mode or os.access(path, os.W_OK)))
        if self.mode.startswith("r"):
            return False
        return os.access(path.parent, os.W_OK)


class FileManagerWithLogging(LogManager, SecureManager, FileManager):
    """Объединяет проверку доступа, логирование и работу с файлом."""

    def __enter__(self):
        if not self.check_permissions():
            raise PermissionError(f"нет доступа к файлу: {self.filename}")
        result = super().__enter__()
        self.log_operation("открыт")
        return result

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.log_operation("закрыт")

    def read(self) -> str:
        result = super().read()
        self.log_operation("прочитан")
        return result

    def write(self, data: str) -> None:
        super().write(data)
        self.log_operation("записан")


def main():
    """Прочитать исходный файл через собственный файловый менеджер."""
    print("Лабораторная 04, вариант B — файловый менеджер")
    source = Path(__file__).resolve()
    with FileManagerWithLogging(str(source), "r") as manager:
        content = manager.read()
        print("Прочитанный файл:", source.name)
        print("Количество символов:", len(content))
    print("Файл закрыт:", manager._file is None)
    print("Порядок MRO:", " -> ".join(cls.__name__ for cls in FileManagerWithLogging.__mro__))


if __name__ == "__main__":
    main()
