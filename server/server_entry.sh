#!/bin/sh

python3.11 -m venv /home/user/mdp-rpi/server/app/venv

. /home/user/mdp-rpi/server/app/venv/bin/activate

echo "Activated venv; starting server"

python /home/user/mdp-rpi/server/app/main.py

echo "Listening for USB ports"

# List all active USB ports
usb_ports=$(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null)

# Check if any USB ports are found
if [ -n "$usb_ports" ]; then
  # Change permissions for each found USB port
  for port in $usb_ports; do
    sudo chmod a+rw "$port"
  done
else
  echo "No active USB ports found."
fi