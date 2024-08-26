#!/bin/sh

# shellcheck disable=SC2164
cd /home/user/mdp-rpi/server/app

python3 -m venv venv

# shellcheck disable=SC3046
source /home/user/mdp-rpi/server/app/venv/bin/activate

pip install -r requirements.txt

