#!/bin/bash
# Restore a backup produced by backup.sh. Refuses to overwrite existing data
# unless FORCE=1, because getting this wrong destroys the reviews.
#
#   ./scripts/restore.sh review-backup-20260828T090000Z.tar.gz [target-dir]
set -euo pipefail

ARCHIVE="${1:?usage: restore.sh <archive.tar.gz> [target-dir]}"
TARGET="${2:-$(cd "$(dirname "$0")/.." && pwd)/data}"

if [ -e "$TARGET/app.db" ] && [ "${FORCE:-0}" != "1" ]; then
  echo "$TARGET/app.db already exists. Move it aside, or re-run with FORCE=1." >&2
  exit 1
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
tar -xzf "$ARCHIVE" -C "$WORK"
sqlite3 "$WORK/data/app.db" "PRAGMA integrity_check;" | grep -qx ok \
  || { echo "Archive is corrupt" >&2; exit 1; }

mkdir -p "$TARGET"
cp "$WORK/data/app.db" "$TARGET/app.db"
rm -rf "$TARGET/pdfs"
[ -d "$WORK/data/pdfs" ] && cp -R "$WORK/data/pdfs" "$TARGET/pdfs"
echo "Restored to $TARGET"
echo "  $(sqlite3 "$TARGET/app.db" 'SELECT COUNT(*) FROM documents;') papers, $(sqlite3 "$TARGET/app.db" 'SELECT COUNT(*) FROM comments;') comments"
