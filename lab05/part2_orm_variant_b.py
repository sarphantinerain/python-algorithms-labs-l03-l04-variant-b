"""Часть 2, вариант B: небольшой ORM с хранилищем в памяти."""

from copy import deepcopy
from math import isfinite


class Field:
    """Дескриптор поля модели с проверкой типа."""

    def __init__(self, field_type, primary_key=False, default=None):
        self.field_type = field_type
        self.primary_key = primary_key
        self.default = default
        self.name = None
        if default is not None:
            self._validate(default)

    def __set_name__(self, owner, name):
        self.name = name

    def _validate(self, value):
        if value is None:
            return
        if self.field_type is int:
            valid = type(value) is int
        elif self.field_type is float:
            valid = type(value) in (int, float) and isfinite(value)
        else:
            valid = isinstance(value, self.field_type)
        if not valid:
            raise TypeError(f"поле {self.name} ожидает {self.field_type.__name__}")

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj, value):
        self._validate(value)
        obj.__dict__[self.name] = value

    def to_db_value(self, value):
        return value

    def from_db_value(self, value):
        return value


class IntegerField(Field):
    """Целочисленное поле; bool не считается целым значением модели."""

    def __init__(self, primary_key=False, default=None):
        super().__init__(int, primary_key=primary_key, default=default)

    def to_db_value(self, value):
        return int(value) if value is not None else None

    def from_db_value(self, value):
        return int(value) if value is not None else None


class StringField(Field):
    """Строковое поле с ограничением длины."""

    def __init__(self, max_length=255, default=None):
        if type(max_length) is not int or max_length <= 0:
            raise ValueError("max_length должен быть положительным целым числом")
        self.max_length = max_length
        super().__init__(str, default=default)

    def _validate(self, value):
        super()._validate(value)
        if value is not None and len(value) > self.max_length:
            raise ValueError(f"строка в поле {self.name} длиннее {self.max_length}")

    def to_db_value(self, value):
        return str(value) if value is not None else None

    def from_db_value(self, value):
        return str(value) if value is not None else None


class FloatField(Field):
    """Вещественное поле, хранящее значение как float."""

    def __init__(self, default=None):
        super().__init__(float, default=default)

    def __set__(self, obj, value):
        self._validate(value)
        obj.__dict__[self.name] = float(value) if value is not None else None

    def to_db_value(self, value):
        return float(value) if value is not None else None

    def from_db_value(self, value):
        return float(value) if value is not None else None


class ModelMeta(type):
    """Собирает поля и выделяет независимое хранилище каждому классу."""

    registry = []

    def __new__(mcs, name, bases, namespace):
        fields = {}
        for base in bases:
            fields.update(getattr(base, "_fields", {}))
        fields.update({key: value for key, value in namespace.items()
                       if isinstance(value, Field)})
        primary_keys = [key for key, value in fields.items() if value.primary_key]
        if name != "Model" and len(primary_keys) != 1:
            raise TypeError("у модели должен быть ровно один первичный ключ")
        namespace["_fields"] = fields
        namespace["_table_name"] = name.lower()
        namespace["_primary_key"] = primary_keys[0] if primary_keys else None
        namespace["_records"] = {}
        namespace["_next_id"] = 1
        cls = super().__new__(mcs, name, bases, namespace)
        if name != "Model":
            mcs.registry.append(cls)
        return cls


class Model(metaclass=ModelMeta):
    """Базовая модель с сохранением строк в памяти и генерацией SQL."""

    def __init__(self, **kwargs):
        unknown = kwargs.keys() - self._fields.keys()
        if unknown:
            raise TypeError(f"неизвестные поля: {', '.join(sorted(unknown))}")
        for name, field in self._fields.items():
            setattr(self, name, kwargs.get(name, deepcopy(field.default)))
        self.last_query = None

    def save(self):
        """Вставить/обновить запись; вернуть параметризованный SQL и параметры."""
        cls = type(self)
        key_name = cls._primary_key
        key = getattr(self, key_name)
        if key is None:
            key = cls._next_id
            setattr(self, key_name, key)
            cls._next_id += 1
        elif type(key) is int and key >= cls._next_id:
            cls._next_id = key + 1
        row = {name: field.to_db_value(getattr(self, name))
               for name, field in cls._fields.items()}
        if key in cls._records:
            names = [name for name in row if name != key_name]
            sql = (f"UPDATE {cls._table_name} SET "
                   + ", ".join(f"{name} = ?" for name in names)
                   + f" WHERE {key_name} = ?")
            params = tuple(row[name] for name in names) + (key,)
        else:
            names = list(row)
            sql = (f"INSERT INTO {cls._table_name} (" + ", ".join(names)
                   + ") VALUES (" + ", ".join("?" for _ in names) + ")")
            params = tuple(row[name] for name in names)
        cls._records[key] = deepcopy(row)
        self.last_query = (sql, params)
        return self.last_query

    def delete(self):
        """Удалить запись; вернуть параметризованный SQL и параметры."""
        cls = type(self)
        key_name = cls._primary_key
        key = getattr(self, key_name)
        if key not in cls._records:
            raise LookupError("запись не найдена")
        del cls._records[key]
        self.last_query = (f"DELETE FROM {cls._table_name} WHERE {key_name} = ?", (key,))
        return self.last_query

    @classmethod
    def _from_row(cls, row):
        return cls(**{name: field.from_db_value(row[name])
                      for name, field in cls._fields.items()})

    @classmethod
    def get(cls, id: int) -> "Model | None":
        row = cls._records.get(id)
        return cls._from_row(row) if row is not None else None

    @classmethod
    def filter(cls, **kwargs) -> list["Model"]:
        return list(QuerySet(cls).filter(**kwargs))

    def __repr__(self) -> str:
        values = ", ".join(f"{name}={getattr(self, name)!r}" for name in self._fields)
        return f"{type(self).__name__}({values})"


class QuerySet:
    """Ленивая цепочка фильтрации, сортировки и ограничения записей."""

    def __init__(self, model_class, filters=(), ordering=None, maximum=None):
        if not issubclass(model_class, Model):
            raise TypeError("QuerySet требует класс Model")
        self.model_class = model_class
        self._filters = filters
        self._ordering = ordering
        self._maximum = maximum

    def filter(self, **kwargs) -> "QuerySet":
        unknown = kwargs.keys() - self.model_class._fields.keys()
        if unknown:
            raise ValueError(f"неизвестные поля: {', '.join(sorted(unknown))}")
        for name, value in kwargs.items():
            self.model_class._fields[name]._validate(value)
        return QuerySet(self.model_class, self._filters + (kwargs,),
                        self._ordering, self._maximum)

    def order_by(self, field: str) -> "QuerySet":
        name = field.removeprefix("-")
        if name not in self.model_class._fields:
            raise ValueError(f"неизвестное поле сортировки: {field}")
        return QuerySet(self.model_class, self._filters, field, self._maximum)

    def limit(self, n: int) -> "QuerySet":
        if type(n) is not int or n < 0:
            raise ValueError("лимит должен быть неотрицательным целым числом")
        return QuerySet(self.model_class, self._filters, self._ordering, n)

    def __iter__(self):
        rows = list(self.model_class._records.values())
        for conditions in self._filters:
            rows = [row for row in rows if all(row[name] == value
                                                for name, value in conditions.items())]
        if self._ordering is not None:
            name = self._ordering.removeprefix("-")
            rows.sort(key=lambda row: (row[name] is None, row[name]),
                      reverse=self._ordering.startswith("-"))
        if self._maximum is not None:
            rows = rows[:self._maximum]
        return (self.model_class._from_row(row) for row in rows)

    def __len__(self):
        return sum(1 for _ in self)

    def first(self) -> "Model | None":
        return next(iter(self), None)

    def count(self) -> int:
        return len(self)


class TransactionManager:
    """Снимок всех таблиц: при ошибке восстанавливает их состояние."""

    def __init__(self):
        self._snapshot = None
        self._active = False

    def __enter__(self):
        if self._active:
            raise RuntimeError("транзакция уже активна")
        self._snapshot = {cls: (deepcopy(cls._records), cls._next_id)
                          for cls in ModelMeta.registry}
        self._active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._active:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        return False

    def commit(self):
        if not self._active:
            raise RuntimeError("нет активной транзакции")
        self._snapshot = None
        self._active = False

    def rollback(self):
        if not self._active:
            raise RuntimeError("нет активной транзакции")
        for cls, (records, next_id) in self._snapshot.items():
            cls._records = records
            cls._next_id = next_id
        self._snapshot = None
        self._active = False


class User(Model):
    """Модель пользователя из шаблона задания."""

    id = IntegerField(primary_key=True)
    name = StringField(max_length=100)
    email = StringField(max_length=255)
    age = IntegerField(default=0)


class Article(Model):
    """Модель статьи из шаблона задания."""

    id = IntegerField(primary_key=True)
    title = StringField(max_length=200)
    content = StringField()
    author_id = IntegerField()
    views = IntegerField(default=0)
