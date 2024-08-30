

setup_bluetooth() {
  echo "Setting up bluetooth configurations"
  # Need to make sure command does not keep on adding the line
  if ! grep -q "ExecStartPost=\/usr\/bin\/sdptool add SP" /lib/systemd/system/bluetooth.service; then
    sudo sed -i 's|ExecStart=/usr/libexec/bluetooth/bluetoothd|ExecStart=/usr/libexec/bluetooth/bluetoothd -C --noplugin=sap\nExecStartPost=/usr/bin/sdptool add SP|' /lib/systemd/system/bluetooth.service
  fi
  sudo systemctl daemon-reload
  sudo systemctl restart bluetooth
}

setup_bluetooth
