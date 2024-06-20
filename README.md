# Astronomy picture of the day fetcher script

This is just a small script to fetch the current
[astronomy picture of the day](https://apod.nasa.gov/) and set the background
(using [swaybg](https://github.com/swaywm/swaybg)).

It will download the images under `~/Images/apod`.

To install you can just run the `utils/install.sh` script (check it out first).
To do manually, see the next sections.

## Build as standalone binary

For this you can use [pyinstaller](https://pyinstaller.org/en/stable/):

```
> poetry run pyinstaller --onefile apod_fetcher.py
> cp dist/apod_fetcher ~/bin  # Or wherever you want it installed
```

## Install as a systemd unit

You have to copy the systemd unit file to `~/.config/systemd/user` creating it
if needed:

```
mkdir -p ~/.config/systemd/user cp apod-fetcher.timer ~/.config/systemd/user/
cp systemd_files/* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable apod-fetcher.timer
systemctl --user list-timers apod-fetcher
# run it for the first time
systemctl start apod-fetcher.timer
```
