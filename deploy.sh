#!/usr/bin/env bash
set -euo pipefail

commit="${1:?full source commit required}"
[[ "$commit" =~ ^[0-9a-f]{40}$ ]] || exit 2
repo=/opt/deploy/flatnotes
root=/opt/flatnotes
exec 8>/run/lock/flatnotes-deploy.lock
flock -n 8 || exit 4
test "$(git -C "$repo" remote get-url origin)" = https://github.com/Forlooong/flatnotes.git
test "$(git -C "$repo" rev-parse "$commit^{commit}")" = "$commit"
test "$(findmnt -rn -M /data -o UUID)" = "6cb900e1-697a-4305-884c-cfd1620f5adf"

install -d -m 0755 /data/apps /data/apps/notes
install -d -m 0750 -o 1000 -g 1000 /data/apps/notes/shared
install -d -m 0700 "$root" "$root/releases"
release="$root/releases/$commit"
test ! -e "$release"
mkdir -m 0755 "$release"
git -C "$repo" archive "$commit" | tar -x -C "$release"
printf 'SOURCE_COMMIT=%s\n' "$commit" > "$release/release.env"
printf '%s\n' "$commit" > "$release/source-commit"
export SOURCE_COMMIT="$commit"
docker compose --progress plain -f "$release/docker-compose.yml" build
docker run --rm --network none --entrypoint python "site-flatnotes:$commit" -m compileall -q /app/server
(cd "$release"; find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
(cd "$release"; sha256sum -c SHA256SUMS >/dev/null)
previous=$(readlink -f "$root/current" || true)
printf '%s\n' "$previous" > "$release/previous-release"
if test -f /etc/systemd/system/flatnotes.service; then
    cp -p /etc/systemd/system/flatnotes.service "$release/previous-service"
fi
rollback() {
    systemctl stop flatnotes.service || true
    if test -n "$previous" && test -f "$previous/release.env"; then
        ln -sfn "$previous" "$root/current.stage"
        mv -fT "$root/current.stage" "$root/current"
        if test -f "$release/previous-service"; then
            install -m 0644 "$release/previous-service" /etc/systemd/system/flatnotes.service
        fi
        systemctl daemon-reload
        systemctl start flatnotes.service
    fi
}
systemctl stop flatnotes.service 2>/dev/null || true
trap rollback ERR
install -m 0644 "$release/flatnotes.service" /etc/systemd/system/flatnotes.service
ln -sfn "$release" "$root/current.stage"
mv -fT "$root/current.stage" "$root/current"
systemctl daemon-reload
systemctl enable flatnotes.service
systemctl start flatnotes.service

python3 - <<'PY'
import json
import time
import urllib.error
import urllib.request

deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen('http://127.0.0.1:18080/apps/notes/health', timeout=3) as response:
            if response.status == 200 and json.load(response) == 'OK':
                print('Flatnotes readiness passed.')
                break
    except (urllib.error.URLError, TimeoutError, ValueError):
        pass
    time.sleep(2)
else:
    raise SystemExit('Flatnotes did not become ready within 45 seconds.')
PY

trap - ERR
printf '%s\n' "$commit" > "$root/current-commit"
date -u +%FT%TZ > "$release/deployed-at"
printf 'flatnotes_source=%s\nflatnotes_release=%s\n' "$commit" "$release"
