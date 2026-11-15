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

# Download the latest Statistics Canada tables into data/raw/
extract:
    uv run python -m public_spend_tracker_pipeline.extract.statcan
