#!/bin/bash

python3.11 -m venv --system-site-packages /home/user/mdp-rpi/server/app/venv

. /home/user/mdp-rpi/server/app/venv/bin/activate

sudo apt update
sudo apt install python3-dev python3-pip build-essential libbluetooth-dev -y

pip install -r /home/user/mdp-rpi/server/app/requirements.txt

sudo apt install -y python3-libcamera python3-kms++
sudo apt install -y python3-prctl libatlas-base-dev ffmpeg libopenjp2-7
sudo apt install -y python3-picamera2
