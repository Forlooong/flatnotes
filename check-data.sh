#!/usr/bin/env bash
set -euo pipefail
test "$(findmnt -rn -M /data -o UUID)" = "6cb900e1-697a-4305-884c-cfd1620f5adf"
test -d /data/apps/notes/shared
