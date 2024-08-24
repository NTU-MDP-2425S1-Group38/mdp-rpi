#!/bin/sh -e

PROJECT_ROOT_GIT="home/pi/mdp-rpi.git"  # matches "~/mdp-rpi.git"
PROJECT_ROOT_DIR="home/pi/mdp-rpi"  # matches "~/mdp-rpi"

cd "$PROJECT_ROOT_DIR"

git --work-tree="$PROJECT_ROOT_DIR" --git-dir="$PROJECT_ROOT_GIT" checkout -f

echo "POST RECEIVE EXECUTED!"