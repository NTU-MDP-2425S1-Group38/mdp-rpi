#!/bin/bash

python3.11 -m venv /home/user/mdp-rpi/server/app/venv

. /home/user/mdp-rpi/server/app/venv/bin/activate

pip install -r /home/user/mdp-rpi/server/app/requirements.txt