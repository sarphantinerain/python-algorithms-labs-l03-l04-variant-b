"""Запуск готовых решений лабораторных 03, 04 и 05 подряд."""

from lab03.variant_b import main as lab03_main
from lab04.variant_b import main as lab04_main
from lab05.part1_cars import main as lab05_part1_main
from lab05.part2_orm_variant_b import main as lab05_part2_main


def main():
    for run in (lab03_main, lab04_main, lab05_part1_main, lab05_part2_main):
        run()
        print()


if __name__ == "__main__":
    main()
