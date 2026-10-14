"""Проверки обеих частей лабораторной 05."""

import unittest
from pathlib import Path

from lab05.part1_cars import Car, SpecMachine, Truck, get_car_list
from lab05.part2_orm_variant_b import (FloatField, IntegerField, Model,
                                       QuerySet, StringField, TransactionManager)


class CarsTests(unittest.TestCase):
    def test_csv_and_class_specific_attributes(self):
        csv_file = Path(__file__).with_name("cars.csv")
        vehicles = get_car_list(csv_file)
        self.assertEqual(len(vehicles), 4)
        self.assertEqual([item.car_type for item in vehicles],
                         ["car", "truck", "truck", "car"])
        self.assertIsInstance(vehicles[0], Car)
        self.assertEqual(vehicles[0].passenger_seats_count, 4)
        self.assertEqual(vehicles[0].get_photo_file_ext(), ".jpeg")
        self.assertFalse(hasattr(vehicles[0], "get_body_volume"))
        self.assertEqual(vehicles[1].get_body_volume(), 60)
        self.assertEqual(vehicles[2].get_body_volume(), 0)
        self.assertFalse(hasattr(vehicles[1], "passenger_seats_count"))

    def test_validation_and_invalid_dimensions(self):
        truck = Truck("Man", "photo.png", 2, "bad")
        self.assertEqual((truck.body_length, truck.body_width, truck.body_height),
                         (0, 0, 0))
        with self.assertRaises(ValueError):
            Car("Mazda", "photo.txt", 2, 4)
        with self.assertRaises(ValueError):
            SpecMachine("Hitachi", "photo.gif", 1, "")


class OrmTests(unittest.TestCase):
    def setUp(self):
        class Product(Model):
            id = IntegerField(primary_key=True)
            name = StringField(max_length=20)
            price = FloatField(default=0.0)

        self.Product = Product

    def test_fields_save_get_filter_delete_and_queryset(self):
        first = self.Product(name="A", price=2)
        sql, params = first.save()
        self.assertTrue(sql.startswith("INSERT INTO product"))
        self.assertEqual(params, (1, "A", 2.0))
        self.assertEqual(self.Product.get(1).price, 2.0)
        first.price = 3.5
        self.assertTrue(first.save()[0].startswith("UPDATE product"))
        self.Product(name="B", price=5).save()
        self.assertEqual([item.name for item in self.Product.filter(price=3.5)], ["A"])
        query = QuerySet(self.Product).order_by("-price").limit(1)
        self.assertEqual(query.first().name, "B")
        self.assertEqual(query.count(), 1)
        self.assertEqual(first.delete()[0], "DELETE FROM product WHERE id = ?")
        self.assertIsNone(self.Product.get(1))
        with self.assertRaises(ValueError):
            self.Product(name="too long for twenty characters")

    def test_commit_and_rollback(self):
        with TransactionManager():
            self.Product(name="saved").save()
        self.assertEqual(QuerySet(self.Product).count(), 1)
        with self.assertRaisesRegex(RuntimeError, "cancel"):
            with TransactionManager():
                self.Product(name="reverted").save()
                raise RuntimeError("cancel")
        self.assertEqual([item.name for item in QuerySet(self.Product)], ["saved"])
        self.assertEqual(self.Product._next_id, 2)


if __name__ == "__main__":
    unittest.main()
