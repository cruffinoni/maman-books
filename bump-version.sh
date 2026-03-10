#!/usr/bin/env bash
set -euo pipefail

usage() {
	echo "Usage: $(basename "$0") [--push] <patch|minor|major>" >&2
	exit 1
}

push=false
if [[ "${1:-}" == "--push" ]]; then
	push=true
	shift
fi

if [[ $# -ne 1 ]]; then
	usage
fi

case "$1" in
	patch|minor|major) ;;
	*) usage ;;
esac

bump="$1"

if ! git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
	echo "Error: must run inside a git repository." >&2
	exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
	echo "Error: working tree is dirty; commit or stash changes first." >&2
	exit 1
fi

config_file="$git_root/config.py"
readme_file="$git_root/README.md"

if [[ ! -f "$config_file" ]]; then
	echo "Error: version file not found at $config_file" >&2
	exit 1
fi

current_version="$(grep -E '_VERSION\s*=\s*"' "$config_file" | head -n 1 \
	| sed -E 's/.*"([0-9]+\.[0-9]+\.[0-9]+)".*/\1/')"
if [[ ! "$current_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	echo "Error: unable to parse current version from $config_file" >&2
	exit 1
fi

IFS='.' read -r major minor patch <<<"$current_version"

case "$bump" in
	patch)
		patch=$((patch + 1))
		;;
	minor)
		minor=$((minor + 1))
		patch=0
		;;
	major)
		major=$((major + 1))
		minor=0
		patch=0
		;;
esac

new_version="${major}.${minor}.${patch}"

tag="v${new_version}"
if git rev-parse -q --verify "refs/tags/${tag}" >/dev/null; then
	echo "Error: tag ${tag} already exists." >&2
	exit 1
fi

perl -0pi -e 's/_VERSION\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"/_VERSION = "'"$new_version"'"/' "$config_file"

if ! grep -q "_VERSION = \"${new_version}\"" "$config_file"; then
	echo "Error: failed to update version in $config_file" >&2
	exit 1
fi

if [[ -f "$readme_file" ]]; then
	sed -i '' "s/v${current_version}/v${new_version}/g" "$readme_file"
	if grep -q "v${current_version}" "$readme_file"; then
		echo "Warning: some occurrences of v${current_version} remain in $readme_file" >&2
	fi
fi

git add "$config_file" "$readme_file"
git commit -m "chore(release): bump version to ${new_version}"
git tag -a "$tag" -m "Release ${tag}"

if [[ "$push" == true ]]; then
	git push origin HEAD
	git push origin "$tag"
fi
