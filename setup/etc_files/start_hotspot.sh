#!/bin/sh -e

sudo nmcli device wifi hotspot ssid MDP_GROUP_38 password password
#sudo nmcli connection modify Hotspot connection.autoconnect yes
sudo nmcli connection modify Hotspot ipv4.addresses 192.168.100.100/16
sudo nmcli connection down Hotspot
sudo nmcli connection up Hotspot
#echo "Executing first boot!" | sudo wall
#
## Update and install required packages
#echo "[SETUP] Updating self" | sudo wall
#sudo apt-get update
#echo "[SETUP] Installing hostapd, dnsmasq, and dhcpd5" | sudo wall
#sudo apt-get install -y hostapd dnsmasq dhcpcd5
#
## Stop services during configuration
#sudo systemctl stop hostapd
#sudo systemctl stop dnsmasq
#
## Configure a static IP for wlan0
#echo "[SETUP] Setting static IP for wlan0" | sudo wall
#cat >> /etc/dhcpcd.conf <<EOF
#interface wlan0
#  static ip_address=192.168.4.1/24
#  nohook wpa_supplicant
#EOF
#
## Restart the DHCP service
#echo "[SETUP] Restarting DHCP service" | sudo wall
#service dhcpcd restart
#
## Configure DNSMasq
#echo "[SETUP] Setting DNSMasq config" | sudo wall
#mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
#cat >> /etc/dnsmasq.conf <<EOF
#interface=wlan0
#dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
#EOF
#
#echo "[SETUP] Starting DNSMasq" | sudo wall
#sudo systemctl start dnsmasq
#
## Configure HostAPD
#echo "[SETUP] Setting hostapd config" | sudo wall
#cat >> /etc/hostapd/hostapd.conf <<EOF
#country_code=SG
#interface=wlan0
#ssid=MDP-group-38
#channel=9
#auth_algs=1
#wpa=2
#wpa_passphrase=raspberry
#wpa_key_mgmt=WPA-PSK
#wpa_pairwise=TKIP CCMP
#rsn_pairwise=CCMP
#EOF
#
## Set DAEMON_CONF in /etc/default/hostapd
#sed -i 's|#DAEMON_CONF="|DAEMON_CONF="/etc/hostapd/hostapd.conf|' /etc/default/hostapd
#
## Sleep to ensure registration of hostapd updates
#sleep 5
#
## Start services on boot
#echo "[SETUP] Enabling services to start" | sudo wall
#sudo systemctl unmask hostapd
#sudo systemctl enable hostapd
#sudo systemctl start hostapd
#
