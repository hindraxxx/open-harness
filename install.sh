#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install.sh [--repo-url URL] [--ref REF] [--install-dir DIR] [--bin-dir DIR]

Installs the harness by cloning or updating the source repo in a stable local
directory, then symlinking the CLI into a local bin directory.

Options:
  --repo-url URL      Git clone URL for the harness source repo.
  --ref REF           Git branch to install or update from. Default: main
  --install-dir DIR   Local clone location. Default: $HOME/.workflow-project
  --bin-dir DIR       Directory that will contain the harness symlink.
                      Default: $HOME/.local/bin
  -h, --help          Show this help text.

Environment:
  HARNESS_REPO_URL    Default repo URL when --repo-url is not provided.
  HARNESS_REF         Default ref when --ref is not provided.
  HARNESS_INSTALL_DIR Default install directory when --install-dir is not provided.
  HARNESS_BIN_DIR     Default bin directory when --bin-dir is not provided.
  HARNESS_LINK_PATH   Full symlink path. Overrides --bin-dir when set.
EOF
}

log() {
  printf '==> %s\n' "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

path_contains() {
  case ":${PATH:-}:" in
    *:"$1":*) return 0 ;;
    *) return 1 ;;
  esac
}

infer_repo_url_from_script() {
  local script_dir repo_url
  script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
  if git -C "$script_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    repo_url=$(git -C "$script_dir" remote get-url origin 2>/dev/null || true)
    if [ -n "$repo_url" ]; then
      printf '%s\n' "$repo_url"
      return 0
    fi
  fi
  return 1
}

repo_url="${HARNESS_REPO_URL:-https://github.com/hindraxxx/workflow-project.git}"
ref="${HARNESS_REF:-main}"
install_dir="${HARNESS_INSTALL_DIR:-$HOME/.workflow-project}"
bin_dir="${HARNESS_BIN_DIR:-$HOME/.local/bin}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo-url)
      [ "$#" -ge 2 ] || die "--repo-url requires a value"
      repo_url="$2"
      shift 2
      ;;
    --ref)
      [ "$#" -ge 2 ] || die "--ref requires a value"
      ref="$2"
      shift 2
      ;;
    --install-dir)
      [ "$#" -ge 2 ] || die "--install-dir requires a value"
      install_dir="$2"
      shift 2
      ;;
    --bin-dir)
      [ "$#" -ge 2 ] || die "--bin-dir requires a value"
      bin_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unexpected argument: $1"
      ;;
  esac
done

if [ -z "$repo_url" ]; then
  repo_url=$(infer_repo_url_from_script || true)
fi

link_path="${HARNESS_LINK_PATH:-$bin_dir/harness}"

need_cmd git
need_cmd ln
need_cmd chmod
need_cmd mkdir

mkdir -p -- "$(dirname -- "$install_dir")"

if [ ! -e "$install_dir" ]; then
  log "cloning harness source into $install_dir"
  git clone --branch "$ref" --single-branch "$repo_url" "$install_dir"
else
  [ -d "$install_dir" ] || die "install dir exists and is not a directory: $install_dir"
  git -C "$install_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    || die "install dir exists and is not a git repo: $install_dir"

  current_origin=$(git -C "$install_dir" remote get-url origin 2>/dev/null || true)
  [ -n "$current_origin" ] || die "existing install dir has no origin remote: $install_dir"
  [ "$current_origin" = "$repo_url" ] || die "existing install dir points to a different origin: $current_origin"

  log "updating existing harness source in $install_dir"
  git -C "$install_dir" fetch origin "$ref"
  git -C "$install_dir" checkout "$ref"
  git -C "$install_dir" pull --ff-only origin "$ref"
fi

[ -f "$install_dir/bin/harness" ] || die "missing harness entrypoint at $install_dir/bin/harness"
chmod +x "$install_dir/bin/harness"

mkdir -p -- "$bin_dir"
ln -sf "$install_dir/bin/harness" "$link_path"

command_name="harness"
if ! path_contains "$bin_dir"; then
  command_name="$link_path"
fi

printf '\nInstalled harness.\n'
printf 'Source repo: %s\n' "$repo_url"
printf 'Install dir: %s\n' "$install_dir"
printf 'Command link: %s\n' "$link_path"

if ! path_contains "$bin_dir"; then
  printf '\n%s\n' "PATH note: $bin_dir is not currently on PATH."
  printf '%s\n' "Add this to your shell profile if you want to run \`harness\` directly:"
  printf '  export PATH="%s:$PATH"\n' "$bin_dir"
fi

printf '\nNext steps:\n'
printf '  cd /path/to/your/project\n'
printf '  %s start your-session-id\n' "$command_name"
printf '  %s update\n' "$command_name"
