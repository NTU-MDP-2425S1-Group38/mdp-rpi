#!/usr/bin/sh -e


PROJECT_ROOT_GIT="/home/user/mdp-rpi.git"  # matches "~/mdp-rpi.git"
PROJECT_ROOT_DIR="/home/user/mdp-rpi"
POST_REC_ORIGINAL_FILE="/etc/mdp/__post_receive.sh"


create_pi_user() {
  sudo useradd -m user
  echo "user:password" | sudo chpasswd
  sudo usermod -aG sudo user
}


create_git_repo() {

  sudo apt install git -y
  git config --global init.defaultBranch main

  # Create git folder if not exist
  if [ ! -r "$PROJECT_ROOT_GIT" ]; then
    sudo mkdir -p "$PROJECT_ROOT_GIT"
    sudo mkdir -p "$PROJECT_ROOT_DIR"
    echo "Created Git repo path! $PROJECT_ROOT_GIT"
    echo "Created Git dir path! $PROJECT_ROOT_DIR"
  else
    echo "Git repo path already exists! $PROJECT_ROOT_GIT"
  fi

  # Init git repo if not init
  cd "$PROJECT_ROOT_GIT"
  if [ ! -d "HEAD" ] ; then
    git init --bare
    echo "Initialised $PROJECT_ROOT_GIT as a git repo!"

      # Copy post-receive hook into the hooks directory
      if [ -f "$POST_REC_ORIGINAL_FILE" ]; then
        sudo cp "$POST_REC_ORIGINAL_FILE" "$PROJECT_ROOT_GIT/hooks/post-receive"
        sudo chmod a+rx "$PROJECT_ROOT_GIT/hooks/post-receive"
        echo "Installed post-receive hook!"
      else
        echo "Post-receive hook script not found at $HOOK_SCRIPT_PATH"
      fi

  else
    echo "$PROJECT_ROOT_GIT is already a git repo!"
  fi

  # Set perms
  sudo chown -Rf user:user "$PROJECT_ROOT_GIT"
  sudo chown -Rf user:user "$PROJECT_ROOT_GIT/objects"
  sudo chown -Rf user:user "$PROJECT_ROOT_DIR"
}

install_global_deps() {
  echo "Installing vim"
  sudo apt install vim -y
  echo "Installing tmux"
  sudo apt install tmux -y
  echo "Installing Python 3.11"
  sudo apt install python3.11 -y
  sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

}

setup_bluetooth() {
  echo "Setting up bluetooth configurations"
  sudo sed -i 's/ExecStart=\/usr\/libexec\/bluetooth\/bluetoothd/ExecStart=\/usr\/libexec\/bluetooth\/bluetoothd -C --noplugin=sap \nExecStartPost=\/usr\/bin\/sdptool add SP/' /lib/systemd/system/bluetooth.service
  sudo systemctl daemon-reload
  sudo systemctl restart bluetooth
}





# Execute functions
create_pi_user
create_git_repo
install_global_deps
setup_bluetooth