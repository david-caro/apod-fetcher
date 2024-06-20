#!/bin/env python3
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from textwrap import wrap

import bs4
import click
import requests

APOD_BASE_URL = "https://apod.nasa.gov/apod"
APOD_URL = f"{APOD_BASE_URL}/astropix.html"
DOWNLOAD_DIR = Path("~/Pictures/apod")
DEST_IMAGE_WIDTH = "1920"
DEST_IMAGE_HEIGHT = "1920"
DEST_IMAGE_SIZE = f"{DEST_IMAGE_WIDTH}x{DEST_IMAGE_HEIGHT}"


class NoNewBG(Exception):
    pass


def do_get(url: str, stream: bool = False) -> requests.Response:
    response = requests.get(
        url,
        headers={
            "User-Agent": "apod_fetcher 0.1.0 https://github.com/david-caro/apod-fetcher"
        },
        stream=stream,
    )
    response.raise_for_status()
    return response


def get_description(page_soup: bs4.BeautifulSoup) -> str:
    match = re.search(
        pattern="Explanation:.*?Tomorrow's",
        string=page_soup.text,
        flags=re.MULTILINE | re.DOTALL,
    )
    raw_text = match.group()[: -len("Tomorrow's")] if match else ""
    return "\n".join(wrap(" ".join(raw_text.split()), width=120))


def download_picture_of_the_day(dest_path: Path) -> str:
    dest_page_path = Path(f"{dest_path}.html")
    if dest_page_path.exists():
        response_text = dest_page_path.read_text(encoding="utf8")
        logging.info(f"    loaded html dump from {dest_page_path}")
        page_soup = bs4.BeautifulSoup(response_text, "html.parser")
    else:

        response = do_get(APOD_URL)
        page_soup = bs4.BeautifulSoup(response.text, "html.parser")
        dest_page_path.write_text(page_soup.prettify())
        logging.info(f"    saved html dump to {dest_page_path}")

    pic_link = page_soup.find_all("a", href=re.compile("image/.*jpg$"))[0]
    with do_get(f"{APOD_BASE_URL}/{pic_link['href']}", stream=True) as pic_response:
        with dest_path.open("wb") as dest_path_df:
            shutil.copyfileobj(pic_response.raw, dest_path_df)

    logging.info(f"    saved picture to {dest_path}")

    return get_description(page_soup)


def add_text(src_image: Path, dest_image: Path, text: str) -> None:
    subprocess.run(
        [
            "convert",
            "-resize",
            DEST_IMAGE_SIZE,
            "-pointsize",
            "20",
            "-fill",
            "yellow",
            "-font",
            "JuliaMono",
            "-gravity",
            "center",
            "-draw",
            f'text 0,300 "{text}"',
            str(src_image),
            str(dest_image),
        ]
    )


def get_todays_picture(download_dir: Path, force: bool = False) -> Path:
    today_stamp = time.strftime("%Y%m%d")
    dest_path = download_dir.expanduser().resolve() / f"{today_stamp}.jpg"
    logging.info(f"Getting today's picture (to {dest_path})")
    if dest_path.exists():
        if not force:
            logging.info("    already exists, skipping")
            raise NoNewBG(f"image already exists at {dest_path}")
        else:
            logging.info("    already exists, but force passed, continuing")

    os.makedirs(dest_path.parent, exist_ok=True)
    orig_img = Path(f"{dest_path}.orig")
    description = download_picture_of_the_day(dest_path=orig_img)

    add_text(src_image=orig_img, dest_image=dest_path, text=description)

    os.remove(orig_img)
    return dest_path


def update_background(bg_path: Path, force: bool = False) -> None:
    subprocess.run(["pkill", "-f", "swaybg"])
    subprocess.Popen(
        [
            "swaybg",
            "-o",
            "*",
            "-i",
            str(bg_path.expanduser().resolve()),
            "-m",
            "fill",
            "-o",
            "HEADLESS-1",
            "-c",
            "#220900",
        ]
    )


@click.command()
@click.option("-f", "--force", is_flag=True)
def main(force: bool) -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        pic_path = get_todays_picture(download_dir=DOWNLOAD_DIR, force=force)
        update_background(bg_path=pic_path, force=force)
    except NoNewBG as error:
        logging.warning("No new background: %s", str(error))


if __name__ == "__main__":
    main()
