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
APOD_URL = f"{APOD_BASE_URL}/ap{{date}}.html"
APOD_TODAY_URL = f"{APOD_BASE_URL}/astropix.html"
DOWNLOAD_DIR = Path("~/Pictures/apod")
LINK_PATH = DOWNLOAD_DIR / "current.jpg"
DEST_IMAGE_WIDTH = 1920
DEST_IMAGE_HEIGHT = 1080
FONT_SIZE = 20
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
    return "\n".join(
        wrap(" ".join(raw_text.split()), width=int(DEST_IMAGE_WIDTH / (FONT_SIZE / 2)))
    )


def download_picture_of_the_day(dest_path: Path, date: str) -> str:
    dest_page_path = Path(f"{dest_path}.html")
    if dest_page_path.exists():
        response_text = dest_page_path.read_text(encoding="utf8")
        logging.info(f"    loaded html dump from {dest_page_path}")
        page_soup = bs4.BeautifulSoup(response_text, "html.parser")
    else:
        response = do_get(APOD_URL.format(date=date))
        page_soup = bs4.BeautifulSoup(response.text, "html.parser")
        dest_page_path.write_text(page_soup.prettify())
        logging.info(f"    saved html dump to {dest_page_path}")

    pic_link = page_soup.find_all("a", href=re.compile("image/.*(jpg|png)$"))[0]
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
            "-background",
            "rgb(0,0,0)",
            "-extent",
            DEST_IMAGE_SIZE,
            "-pointsize",
            f"{FONT_SIZE}",
            "-fill",
            "yellow",
            "-gravity",
            "center",
            "-draw",
            f'text 0,{DEST_IMAGE_HEIGHT/3 - len(text.splitlines())} "{text}"',
            str(src_image),
            str(dest_image),
        ]
    )


def get_picture(
    download_dir: Path, force: bool = False, date: str | None = None
) -> Path:
    if not date or date == "today":
        today_stamp = time.strftime("%y%m%d")
    else:
        today_stamp = date

    dest_path = download_dir.expanduser().resolve() / f"{today_stamp}.jpg"
    logging.info(f"Getting {today_stamp}'s picture (to {dest_path})")
    if dest_path.exists():
        if not force:
            logging.info("    already exists, skipping")
            raise NoNewBG(f"image already exists at {dest_path}")
        else:
            logging.info("    already exists, but force passed, continuing")

    os.makedirs(dest_path.parent, exist_ok=True)
    orig_img = Path(f"{dest_path}.orig")
    description = download_picture_of_the_day(dest_path=orig_img, date=today_stamp)

    add_text(src_image=orig_img, dest_image=dest_path, text=description)

    os.remove(orig_img)
    return dest_path


def on_gnome() -> bool:
    logging.info("Checking window manager...")
    if os.environ.get("XDG_CURRENT_DESKTOP", "").lower() == "gnome":
        logging.info("   got it from XDG_CURRENT_DESKTOP: gnome")
        return True

    elif os.environ.get("XDG_CURRENT_DESKTOP", "") == "":
        # fallback, as the XDG_CURRENT_DESKTOP MIGHT NOT BE SET
        try:
            subprocess.check_call(
                ["pgrep", "sway"],
            )
        except subprocess.CalledProcessError:
            return True

        return False

    logging.info(
        "   got it from XDG_CURRENT_DESKTOP: %s", os.environ["XDG_CURRENT_DESKTOP"]
    )
    return False


def update_background(bg_path: Path) -> None:
    logging.info("updating background")
    if on_gnome():
        logging.info("Using gnome")
        update_background_gnome(bg_path=bg_path)
    else:
        logging.info("Using sway")
        update_background_sway(bg_path=bg_path)


def update_background_gnome(bg_path: Path) -> None:
    change_setting_command = [
        "gsettings",
        "set",
        "org.gnome.desktop.background",
    ]
    subprocess.Popen(
        change_setting_command
        + [
            "picture-uri",
            f"file://{bg_path.expanduser().resolve()}",
        ]
    )
    subprocess.Popen(
        change_setting_command
        + [
            "picture-uri-dark",
            f"file://{bg_path.expanduser().resolve()}",
        ]
    )


def update_background_sway(bg_path: Path) -> None:
    subprocess.run(["pkill", "-f", "swaybg"])
    subprocess.Popen(
        [
            "swaybg",
            "--output",
            "*",
            "--image",
            str(bg_path.expanduser().resolve()),
            "--mode",
            "fit",
            "--color",
            "000000",
        ]
    )


def rotate_image(folder: Path, link: Path) -> None:
    link = link.expanduser()
    folder = folder.expanduser().resolve()

    all_images = [
        image
        for image in sorted(
            list(folder.glob(pattern="*.jpg")),
            key=lambda image: str(image),
        )
        if image != link
    ]
    if not all_images:
        raise Exception(f"No apod images foud!: {all_images}")

    next_index = 0
    if link.exists():
        cur_image = link.resolve()

        if cur_image in all_images:
            next_index = (all_images.index(cur_image) + 1) % len(all_images)

    next_image = all_images[next_index]

    link.unlink(missing_ok=True)
    os.symlink(dst=link, src=next_image)

    update_background(bg_path=link)


@click.command()
@click.option("-f", "--force", is_flag=True)
@click.option("-r", "--rotate", is_flag=True)
@click.option("-d", "--date", default="today", type=str)
def main(rotate: bool, force: bool, date: str) -> None:
    logging.basicConfig(level=logging.INFO)
    if rotate:
        rotate_image(folder=DOWNLOAD_DIR, link=LINK_PATH)
        return

    try:
        pic_path = get_picture(download_dir=DOWNLOAD_DIR, force=force, date=date)
        update_background(bg_path=pic_path)
        return

    except NoNewBG as error:
        logging.warning("No new background: %s", str(error))
        return


if __name__ == "__main__":
    main()
