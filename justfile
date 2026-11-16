# Every command for this project. Run `just` to list them.
# Install just with: brew install just

# List the available commands
default:
    @just --list

# Install Python, the site's packages and every dependency
setup:
    uv sync --all-packages
    pnpm --dir web install

# Run all tests
test:
    uv run pytest

# Check code style and formatting
lint:
    uv run ruff check .
    uv run ruff format --check .

# Download new Statistics Canada releases into data/raw/
extract:
    uv run pst extract

# Build the database from everything downloaded, checking every step
build:
    uv run pst build

# Download, then build: the everyday command
update:
    uv run pst update

# Show downloads, builds and the approved build (changes nothing)
status:
    uv run pst status

# Write the newest complete build's figures as JSON for the site (web/data/)
export:
    uv run pst export

# Install the site's packages (needs pnpm: corepack enable pnpm)
web-setup:
    pnpm --dir web install

# Run the site locally with live reload, at http://localhost:5173
web-dev:
    pnpm --dir web dev

# Build the site into web/build/ from web/data/ (run "just export" first)
web-build:
    pnpm --dir web build

# Serve the built site at http://localhost:4173
web-preview:
    pnpm --dir web preview

# Check the site: types, formatting and lint, tests
web-check:
    pnpm --dir web check
    pnpm --dir web lint
    pnpm --dir web test

# Export the newest build, then build the site
site: export web-build
