# Every command for this project. Run `just` to list them.
# Install just with: brew install just

# List the available commands
default:
    @just --list

# Install Python and every dependency
setup:
    uv sync --all-packages

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
