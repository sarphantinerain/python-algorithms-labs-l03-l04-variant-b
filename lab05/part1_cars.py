"""Часть 1: иерархия транспортных средств и загрузка CSV."""

import csv
import math
import os


class CarBase:
    """Общие поля всех видов техники."""

    __slots__ = ("car_type", "brand", "photo_file_name", "carrying")
    _allowed_extensions = {".jpg", ".jpeg", ".png", ".gif"}

    def __init__(self, brand, photo_file_name, carrying):
        if type(self) is CarBase:
            raise TypeError("создайте Car, Truck или SpecMachine")
        if not isinstance(brand, str) or not brand.strip():
            raise ValueError("марка должна быть непустой строкой")
        if not isinstance(photo_file_name, str) or not photo_file_name.strip():
            raise ValueError("имя фотографии должно быть непустой строкой")
        if os.path.splitext(photo_file_name)[1].lower() not in self._allowed_extensions:
            raise ValueError("недопустимое расширение фотографии")
        carrying = float(carrying)
        if not math.isfinite(carrying) or carrying < 0:
            raise ValueError("грузоподъёмность должна быть конечным неотрицательным числом")
        self.car_type = type(self)._car_type
        self.brand = brand.strip()
        self.photo_file_name = photo_file_name.strip()
        self.carrying = carrying

    def get_photo_file_ext(self):
        return os.path.splitext(self.photo_file_name)[1]


class Car(CarBase):
    """Легковой автомобиль."""

    __slots__ = ("passenger_seats_count",)
    _car_type = "car"

    def __init__(self, brand, photo_file_name, carrying, passenger_seats_count):
        super().__init__(brand, photo_file_name, carrying)
        seats = int(passenger_seats_count)
        if seats <= 0:
            raise ValueError("количество пассажирских мест должно быть положительным")
        self.passenger_seats_count = seats


class Truck(CarBase):
    """Грузовик; некорректные габариты заменяются тремя нулями."""

    __slots__ = ("body_length", "body_width", "body_height")
    _car_type = "truck"

    def __init__(self, brand, photo_file_name, carrying, body_whl):
        super().__init__(brand, photo_file_name, carrying)
        try:
            dimensions = [float(part.strip()) for part in body_whl.split("x")]
            if len(dimensions) != 3 or not all(
                math.isfinite(value) and value > 0 for value in dimensions
            ):
                raise ValueError("некорректные габариты")
        except (AttributeError, TypeError, ValueError):
            dimensions = [0.0, 0.0, 0.0]
        self.body_length, self.body_width, self.body_height = dimensions

    def get_body_volume(self):
        return self.body_length * self.body_width * self.body_height


class SpecMachine(CarBase):
    """Специальная техника с описанием."""

    __slots__ = ("extra",)
    _car_type = "spec_machine"

    def __init__(self, brand, photo_file_name, carrying, extra):
        super().__init__(brand, photo_file_name, carrying)
        if not isinstance(extra, str) or not extra.strip():
            raise ValueError("описание спецтехники должно быть непустым")
        self.extra = extra.strip()


def get_car_list(csv_filename):
    """Прочитать CSV с разделителем ;, пропуская строки с неверными данными."""
    car_list = []
    with open(csv_filename, newline="", encoding="utf-8-sig") as source:
        reader = csv.reader(source, delimiter=";")
        next(reader, None)  # Заголовок CSV.
        for row in reader:
            if len(row) != 7:
                continue
            car_type, brand, seats, photo, body, carrying, extra = row
            try:
                if car_type == "car":
                    vehicle = Car(brand, photo, carrying, seats)
                elif car_type == "truck":
                    vehicle = Truck(brand, photo, carrying, body)
                elif car_type == "spec_machine":
                    vehicle = SpecMachine(brand, photo, carrying, extra)
                else:
                    continue
            except (TypeError, ValueError, OverflowError):
                continue
            car_list.append(vehicle)
    return car_list
