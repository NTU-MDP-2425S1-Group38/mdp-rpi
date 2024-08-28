# RPI Server Code

This dir contains all the code for running the RPI as a server.

When plugging in the usb, need to run the following command to get the RPI to recognize the usb:

```bash
sudo chmod a+rw /dev/ttyUSB1
```

To pull the latest code from the repo to the rpi, run the following command in order:

On laptop:

```bash
git remote add rpi user@192.168.100.100:/home/user/mdp-rpi.git
git push rpi main

```

On RPI:

```bash
chmod +x server_entry.sh
chmod +x server_install_deps.sh
```

Command Format to Send to STM to move:

Direction, Speed, Angle, Distance

Examples:
direction | command
--- | ---
Forward | T,10,0,30
Forward-Right | T,10,25,90
Forward-Left | T,10,-25,90
Backward | t,10,0,30
Backward-Right | t,10,25,90
Backward-Left | t,10,-25,90

For Bluetooth:
https://bluedot.readthedocs.io/en/latest/pairpiandroid.html

sudo apt install libbluetooth-dev
sudo apt-get install python3-dev
pip install git+https://github.com/pybluez/pybluez.git#egg=pybluez
