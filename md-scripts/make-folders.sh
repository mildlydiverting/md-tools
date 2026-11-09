while IFS= read -r folder; do
  mkdir -p "$folder"
done << 'EOF'
are.na-toolkit
art-nuclear-research
dt-arts-geodata
dt-knowledge-base
dt-process-class-notes
md-pkim-classification
md-pkim-library
md-scripts
md-tools
md-twitter-archive
md-webspace-backup-2024-10
md-zenburn
wk-clients
EOF