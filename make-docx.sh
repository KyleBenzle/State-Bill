#!/usr/bin/env bash
# Regenerate the Word documents in docx/ from the Markdown sources. The .md files are never modified.
#   ./make-docx.sh          Word files only
#   ./make-docx.sh --pdf    also make PDFs in pdf/ (needs LibreOffice)
set -e
cd "$(dirname "$0")"
mkdir -p docx
T=templates

for f in 0*.md 1*.md; do
  base="${f%.md}"
  case "$base" in
    05-Proposed-Statutory-Language)   # Ohio pre-introduction bill draft
      pandoc "$f" -f markdown-fancy_lists --lua-filter="$T/redline.lua" \
        --reference-doc="$T/bill-reference.docx" -o "docx/$base.docx" ;;
    11-Sponsor-Brief)                 # two-page brief with real footnotes
      pandoc "$f" -f markdown --lua-filter="$T/footnotes.lua" --lua-filter="$T/no-rules.lua" \
        --reference-doc="$T/brief-reference.docx" -o "docx/$base.docx" ;;
    *)                                # supporting memoranda
      pandoc "$f" -f markdown --lua-filter="$T/no-rules.lua" \
        --reference-doc="$T/memo-reference.docx" -o "docx/$base.docx" ;;
  esac
  echo "docx/$base.docx"
done

if [ "$1" = "--pdf" ]; then
  mkdir -p pdf
  soffice --headless --convert-to pdf --outdir pdf docx/*.docx >/dev/null 2>&1
  echo "PDFs written to pdf/"
fi
