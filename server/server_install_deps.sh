#!/bin/bash

# shellcheck disable=SC2164
cd /home/user/mdp-rpi/server/app

python3.11 -m venv /home/user/mdp-rpi/server/app/venv

# shellcheck disable=SC3046
. /home/user/mdp-rpi/server/app/venv/bin/activate

pip install -r requirements.txt

