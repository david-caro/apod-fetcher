#!/bin/bash

set -e exiterr
set -e nounset
set -e pipefail


SYSTEMD_PATH=~/.config/systemd/user/
BIN_PATH=~/bin/


main() {
    local curdir
    curdir="$(dirname "$(realpath "$0")")"

    cd "$curdir/.."
    poetry run pyinstaller --onefile apod_fetcher.py
    cp dist/apod_fetcher "$BIN_PATH"
    [[ -d "$SYSTEMD_PATH" ]] || mkdir -p "$SYSTEMD_PATH"
    cp systemd_files/* "$SYSTEMD_PATH/"
    sed -i -e "s|^ExecStart.*|ExecStart=$BIN_PATH/apod_fetcher|" "$SYSTEMD_PATH/apod-fetcher.service"
    sed -i -e "s|^ExecStart.*|ExecStart=$BIN_PATH/apod_fetcher --rotate|" "$SYSTEMD_PATH/apod-fetcher-rotate.service"
    systemctl --user daemon-reload
    systemctl --user enable apod-fetcher.timer
    systemctl --user start apod-fetcher.timer
    systemctl --user enable apod-fetcher-rotate.timer
    systemctl --user start apod-fetcher-rotate.timer
}


main "$@"
