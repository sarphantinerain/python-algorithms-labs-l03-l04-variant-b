"""Проверка домашних заданий варианта B лабораторных 03 и 04."""

import unittest
from unittest.mock import mock_open, patch

from lab03.variant_b import (aggregate, average, batch_process, cartesian,
                             concatenate, create_pipeline, even_squares_pipeline,
                             filter_by_type, generate_numbers, group_sorted,
                             pairs, sum_values, take)
from lab04.variant_b import FileManager, FileManagerWithLogging, ValidatedMode


class Lab03VariantBTests(unittest.TestCase):
    def test_pipeline_and_aggregation(self):
        self.assertEqual(even_squares_pipeline()(generate_numbers(0, 6)), 20)
        self.assertEqual(create_pipeline(sum_values)(range(4)), 6)
        self.assertEqual(aggregate(iter([2, 4]), average), 3)
        with self.assertRaises(ValueError):
            average(iter([]))

    def test_lazy_components_and_itertools(self):
        self.assertEqual(list(batch_process(range(5), 2)), [[0, 1], [2, 3], [4]])
        self.assertEqual(list(filter_by_type([1, "x", 2], int)), [1, 2])
        self.assertEqual(list(group_sorted([1, 1, 2], lambda x: x)),
                         [(1, [1, 1]), (2, [2])])
        self.assertEqual(list(take(range(100), 3)), [0, 1, 2])
        self.assertEqual(list(concatenate([1], [2])), [1, 2])
        self.assertEqual(list(pairs([1, 2, 3])), [(1, 2), (1, 3), (2, 3)])
        self.assertEqual(list(cartesian([1, 2], [3])), [(1, 3), (2, 3)])
        with self.assertRaises(ValueError):
            list(batch_process(range(3), 0))


class Lab04VariantBTests(unittest.TestCase):
    def test_context_manager_and_descriptors(self):
        manager = FileManager("data.txt", "w")
        with patch("builtins.open", mock_open()) as opened:
            with manager as file:
                file.write("текст")
            opened.assert_called_once_with("data.txt", "w", encoding="utf-8")
            opened().write.assert_called_once_with("текст")
            opened().close.assert_called_once()
        self.assertIsNone(manager._file)
        with patch("builtins.open", mock_open(read_data="текст")):
            with patch.object(FileManagerWithLogging, "check_permissions", return_value=True):
                with FileManagerWithLogging("data.txt", "r") as file:
                    self.assertEqual(file.read(), "текст")
        with self.assertRaises(ValueError):
            FileManager("data.txt", "invalid")
        with self.assertRaises(ValueError):
            FileManager("bad?.txt", "r")
        self.assertEqual(ValidatedMode.ALLOWED_MODES,
                         {"r", "w", "a", "r+", "w+", "a+"})

    def test_context_does_not_hide_exception(self):
        manager = FileManager("data.txt", "w")
        with patch("builtins.open", mock_open()):
            with self.assertRaisesRegex(RuntimeError, "ошибка"):
                with manager:
                    raise RuntimeError("ошибка")
        self.assertIsNone(manager._file)


if __name__ == "__main__":
    unittest.main()
