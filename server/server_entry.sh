#!/bin/sh

python3.11 -m venv /home/user/mdp-rpi/server/app/venv

. /home/user/mdp-rpi/server/app/venv/bin/activate

echo "Activated venv; starting server"

python /home/user/mdp-rpi/server/app/main.py