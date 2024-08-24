#!/bin/sh -e

DNS_SERVERS=$(nmcli device show eth0 | grep IP4.DNS | awk '{print $2}')

sudo nmcli device wifi hotspot ssid MDP_GROUP_38 password password
nmcli connection modify Hotspot ipv4.dns "$DNS_SERVERS"
sudo nmcli connection modify Hotspot ipv4.addresses 192.168.100.100/16
sudo nmcli connection down Hotspot
sudo nmcli connection up Hotspot


