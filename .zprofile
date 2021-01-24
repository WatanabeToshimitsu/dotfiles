##################
# auto ssh-agent #
##################
if [ -z "$SSH_AUTH_SOCK" ]; then
  echo "Check for a currently running instance of the agent"
  RUNNING_AGENT="`ps -ax | grep 'ssh-agent -s' | grep -v grep | wc -l | tr -d '[:space:]'`"
  if [ "$RUNNING_AGENT" = "0" ]; then
    echo "Launch a new instance of the agent"
    ssh-agent -s &> ~/.ssh/ssh-agent
    ssh-add
  fi
    eval `cat ~/.ssh/ssh-agent`
fi
