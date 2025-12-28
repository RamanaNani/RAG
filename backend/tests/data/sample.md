cat << 'EOF' > tests/data/sample.md
# Introduction

This markdown file is used for testing chunking logic.
It contains headings and multiple paragraphs.

The chunker should preserve headings as section markers.

## Methods

This section describes methods. The content is intentionally long.
This section describes methods. The content is intentionally long.
This section describes methods. The content is intentionally long.
This section describes methods. The content is intentionally long.

## Results

Results are presented here. They should appear in separate chunks
if the size threshold is exceeded.
EOF
