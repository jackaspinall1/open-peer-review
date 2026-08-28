#!/bin/bash
# Consistent backup of the review data: the SQLite database and the PDFs.
#
# The database must be copied with sqlite3 .backup rather than cp: it runs in
# WAL mode, so a plain file copy can capture a database whose committed data
# still lives in a separate write-ahead log.
#
#   ./scripts/backup.sh [output-dir]     (default: ./backups)
set -euo pipefail

DATA_DIR="${DATA_DIR:-$(cd "$(dirname "$0")/.." && pwd)/data}"
OUT="${1:-$(cd "$(dirname "$0")/.." && pwd)/backups}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

[ -f "$DATA_DIR/app.db" ] || { echo "No database at $DATA_DIR/app.db" >&2; exit 1; }
mkdir -p "$OUT" "$WORK/data"

sqlite3 "$DATA_DIR/app.db" ".backup '$WORK/data/app.db'"
sqlite3 "$WORK/data/app.db" "PRAGMA integrity_check;" | grep -qx ok \
  || { echo "Backup failed its integrity check" >&2; exit 1; }

if [ -d "$DATA_DIR/pdfs" ]; then cp -R "$DATA_DIR/pdfs" "$WORK/data/pdfs"; fi

ARCHIVE="$OUT/review-backup-$STAMP.tar.gz"
tar -czf "$ARCHIVE" -C "$WORK" data
echo "$ARCHIVE"
echo "  $(sqlite3 "$WORK/data/app.db" 'SELECT COUNT(*) FROM documents;') papers, $(sqlite3 "$WORK/data/app.db" 'SELECT COUNT(*) FROM comments;') comments, $(du -sh "$ARCHIVE" | cut -f1)"
