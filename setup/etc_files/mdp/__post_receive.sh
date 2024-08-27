#!/bin/sh -e

PROJECT_ROOT_GIT="/home/user/mdp-rpi.git"  # matches "~/mdp-rpi.git"
PROJECT_ROOT_DIR="/home/user/mdp-rpi"  # matches "~/mdp-rpi"

cd "$PROJECT_ROOT_DIR"

git --work-tree="$PROJECT_ROOT_DIR" --git-dir="$PROJECT_ROOT_GIT" checkout -f main

# Read the old and new revision and the reference name
#while read oldrev newrev refname; do
#    # Check if requirements.txt has changed
#    if git diff --name-only $oldrev $newrev | grep -q '^requirements.txt$'; then
#        echo "requirements.txt has changed."
#        chmod +x /home/pi/mdp-rpi/server/server_install_deps.sh
#        /home/pi/mdp-rpi/server/server_install_deps.sh
#    else
#        echo "requirements.txt has not changed."
#    fi
#done

#
#chmod +x /home/user/mdp-rpi/server/server_install_deps.sh
#/home/user/mdp-rpi/server/server_install_deps.sh
#
#chmod +x /home/user/mdp-rpi/server/server_entry.sh
#/home/user/mdp-rpi/server/server_entry.sh &
