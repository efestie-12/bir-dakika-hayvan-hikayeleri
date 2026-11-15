#!/usr/bin/env bash
# Download a free Turkish Piper voice (fahrettin | dfki | fettah) into $TR_VOICE_DIR (default ~/tts)
set -euo pipefail
V="${1:-fahrettin}"
D="${TR_VOICE_DIR:-$HOME/tts}"
mkdir -p "$D"
if [ ! -d "$D/vits-piper-tr_TR-$V-medium" ]; then
  curl -sL "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-tr_TR-$V-medium.tar.bz2" | tar xj -C "$D"
fi
ls "$D/vits-piper-tr_TR-$V-medium"
