#!/usr/bin/env bash
# Make sure purrfile can write each output path it was given.
#
# Docker-based actions such as Platane/snk run as root, so the folder they write (dist/) and the
# files in it belong to root, and the runner user cannot add or replace files there. GitHub-hosted
# runners allow passwordless sudo, so we take ownership back. Never fails the job: if a folder stays
# unwritable, purrfile itself warns and leaves those files untouched.
set -u

for path in "$@"; do
  [ -n "$path" ] || continue
  dir=$(dirname -- "$path")
  mkdir -p -- "$dir" 2>/dev/null || true
  writable() { [ -w "$dir" ] && { [ ! -e "$path" ] || [ -w "$path" ]; }; }
  writable && continue
  chmod -R u+w -- "$dir" 2>/dev/null || true   # enough when we already own it
  writable && continue
  if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo -n chown -R "$(id -u):$(id -g)" -- "$dir" && chmod -R u+w -- "$dir"
  fi
  writable || echo "::warning::purrfile: $dir is not writable by $(id -un), so $path cannot be written"
done
exit 0
