#!/bin/bash
set -euo pipefail
if [[ ${SSH_ORIGINAL_COMMAND:-} =~ ^deploy\ ([0-9a-f]{40})$ ]]; then
    exec sudo -n /usr/bin/python3 /opt/codyssey-aichat/deploy.py "${BASH_REMATCH[1]}"
fi
echo 'Only deploy <40-character commit SHA> is permitted.' >&2
exit 1
