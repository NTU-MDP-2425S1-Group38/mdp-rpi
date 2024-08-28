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
```

On RPI:

```bash
git pull origin main
chmod +x server_entry.sh
chmdo +x server_install_deps.sh
```
