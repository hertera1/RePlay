"""
Библиотека рекомендательных систем Лаборатории по искусственному интеллекту.
"""
import logging
from os.path import join

from sponge_bob_magic.data_loader.loaders import download_dataset


def download_movielens(path: str = ".", dataset: str = "ml-latest-small"):
    """
    Скачать датасет с https://grouplens.org/datasets/movielens/
    Доступные варианты: ml-20m, ml-latest-small, ml-latest и другие, смотри на
    сайте.

    :param path: куда положить
    :param dataset: версия мувиленса
    :return: None
    """

    logging.info("Downloading %s from grouplens...", dataset)
    archive = dataset + ".zip"
    path = join(path, archive)
    url = f"http://files.grouplens.org/datasets/movielens/{archive}"
    download_dataset(url, path)


def download_rekko(path: str = "."):
    """
    Скачать датасет с rekko chalenge
    https://boosters.pro/championship/rekko_challenge/data
    175MB

    :param path: куда положить
    :return:  None
    """
    logging.info("Downloading rekko challenge dataset...")
    archive = "rekko_challenge_rekko_challenge_2019.zip"
    url = f"https://boosters.pro/api/ch/files/pub/{archive}"
    path = join(path, "rekko.zip")
    download_dataset(url, path)
