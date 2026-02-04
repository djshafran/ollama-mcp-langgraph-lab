#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d "Heritage_Platform" || ! -d "Heritage_Resources" || ! -d "Zen" ]]; then
  echo "Missing Heritage repos. Run scripts/heritage/00_fetch.sh first."
  exit 1
fi

DOCKER_CONFIG_DIR="${DOCKER_CONFIG_DIR:-$ROOT_DIR/.docker-nocreds}"
mkdir -p "$DOCKER_CONFIG_DIR"
if [[ ! -f "$DOCKER_CONFIG_DIR/config.json" ]]; then
  echo '{"auths":{}}' > "$DOCKER_CONFIG_DIR/config.json"
fi

CONFIG_FILE="Heritage_Platform/SETUP/config.local.txt"
cat > "$CONFIG_FILE" <<'CFG'
PLATFORM='Station'
TRANSLIT='VH'
LEXICON='MW'
DISPLAY='roma'
SERVERHOST='127.0.0.1'
SERVERPUBLICDIR='/var/www/html/sanskrit/'
SKTDIRURL='/html/sanskrit/'
SKTRESOURCES='/work/Heritage_Resources/'
CGIBINURL='/cgi-bin/SKT/'
CGIDIR='/usr/lib/cgi-bin/SKT/'
CGIEXT=''
MOUSEACTION='CLICK'
CAPTION='Local Heritage Build'
ZENDIR='/work/Zen/ML'
CFG

ln -sf "config.local.txt" "Heritage_Platform/SETUP/config"
ln -sfn "/work/Zen/ML" "Heritage_Platform/ZEN"

if [[ ! -f "Zen/Makefile" ]]; then
  cat > "Zen/Makefile" <<'MK'
all:
	$(MAKE) -C ML
MK
fi

BUILDER_IMAGE="${BUILDER_IMAGE:-ocaml/opam:debian-11-ocaml-4.07}"
echo "Building Heritage_Platform in a builder container ($BUILDER_IMAGE)..."
DOCKER_CONFIG="$DOCKER_CONFIG_DIR" docker run --rm \
  -v "$ROOT_DIR:/work" \
  -w /work/Heritage_Platform \
  "$BUILDER_IMAGE" \
  bash -lc 'sudo -n apt-get update && sudo -n apt-get install -y m4 make gcc python3 && opam update >/dev/null && opam install -y camlp4 ocamlfind camlp-streams >/dev/null && eval $(opam env) && (python3 -m lib2to3 -w configure >/dev/null 2>&1 || true) && python3 ./configure && sed -i "s/^LINK=.*/LINK=ocamlopt -I ..\\/ZEN -I +camlp4 dynlink.cmxa camlp4lib.cmxa/" ML/Makefile && sudo -n mkdir -p /var/www/html/sanskrit/DATA && sudo -n touch /var/www/html/sanskrit/DATA/cache.txt && (make -C /work/Zen/ML clean || true) && find ML -type f \( -name "*.cmi" -o -name "*.cmx" -o -name "*.cmo" -o -name "*.o" -o -name "*.cmxa" -o -name "*.cma" -o -name "*.a" -o -name "*.annot" -o -name "*.cmt" -o -name "*.cmti" \) -delete && make'

echo "Build complete."
