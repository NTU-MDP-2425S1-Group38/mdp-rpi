#!/bin/sh -e

sudo nmcli device wifi hotspot ssid MDP_GROUP_38 password password
sudo nmcli connection modify Hotspot ipv4.addresses 192.168.100.100/16
sudo nmcli connection down Hotspot
sudo nmcli connection up Hotspot

