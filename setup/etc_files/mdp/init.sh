#!/usr/bin/sh -e


PROJECT_ROOT_GIT="/home/pi/mdp-rpi.git"  # matches "~/mdp-rpi.git"
POST_REC_ORIGINAL_FILE="/etc/mdp/__post_receive.sh"

create_git_repo() {

  # Create git folder if not exist
  if [ ! -r "$PROJECT_ROOT_GIT" ]; then
    mkdir -p "$PROJECT_ROOT_GIT"
    echo "Created Git repo path! $PROJECT_ROOT_GIT"
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
        cp "$POST_REC_ORIGINAL_FILE" "$PROJECT_ROOT_GIT/hooks/post-receive"
        chmod +x "$PROJECT_ROOT_GIT/hooks/post-receive"
        echo "Installed post-receive hook!"
      else
        echo "Post-receive hook script not found at $HOOK_SCRIPT_PATH"
      fi

  else
    echo "$PROJECT_ROOT_GIT is already a git repo!"
  fi


}



# Execute functions
create_git_repo
