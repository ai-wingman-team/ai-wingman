# ============================================================================
# AI Wingman - Development Automation
# ============================================================================
# Usage: make <target>
# Example: make setup

.PHONY: help setup start stop restart clean test lint format db-shell logs

# Default target: show help
help:
	@echo "AI Wingman - Available Commands"
	@echo "================================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup       - Initial project setup (run once)"
	@echo "  make install     - Install/update Python dependencies"
	@echo ""
	@echo "Database Management:"
	@echo "  make start       - Start database services"
	@echo "  make stop        - Stop database services"
	@echo "  make restart     - Restart database services"
	@echo "  make db-shell    - Open PostgreSQL shell"
	@echo "  make db-reset    - Reset database (WARNING: deletes data!)"
	@echo ""
	@echo "Development:"
	@echo "  make logs        - View database logs"
	@echo "  make test        - Run test suite"
	@echo "  make lint        - Run code linters"
	@echo "  make format      - Format code with black"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       - Remove generated files"
	@echo "  make clean-all   - Remove everything (including venv & data)"

# One-time project setup
setup:
	@echo " Setting up AI Wingman development environment..."
	@echo ""
	
	# Check Python version
	@python3 --version | grep -q "Python 3\.[9-9]\|Python 3\.1[0-9]" || \
		(echo " Python 3.9+ required" && exit 1)
	@echo " Python version OK"
	
	# Check Docker
	@command -v docker >/dev/null 2>&1 || \
		(echo " Docker not found. Install from https://docker.com" && exit 1)
	@echo " Docker found"
	
	# Create virtual environment
	@echo " Creating virtual environment..."
	@python3 -m venv venv
	
	# Upgrade pip
	@echo "  Upgrading pip..."
	@. venv/bin/activate && pip install --upgrade pip -q
	
	# Install dependencies
	@echo " Installing Python packages..."
	@. venv/bin/activate && pip install -r requirements.txt -q
	
	# Create .env from template
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo " Created .env file from template"; \
		echo "  IMPORTANT: Edit .env with your Slack tokens"; \
	else \
		echo "  .env already exists"; \
	fi
	
	# Start database
	@echo " Starting PostgreSQL with pgvector..."
	@docker compose up -d
	
	# Wait for database
	@echo " Waiting for database to be ready..."
	@sleep 5
	
	@echo ""
	@echo " Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env file with your Slack tokens"
	@echo "2. Activate virtualenv: source venv/bin/activate"
	@echo "3. Run: make start"

# Install/update dependencies
install:
	@echo " Installing dependencies..."
	@. venv/bin/activate && pip install -r requirements.txt

# Start services
start:
	@echo " Starting AI Wingman services..."
	@docker compose up -d
	@echo " Database running at localhost:5433"
	@echo ""
	@echo "To view logs: make logs"
	@echo "To stop: make stop"

# Stop services
stop:
	@echo " Stopping AI Wingman services..."
	@docker compose down
	@echo " Services stopped"

# Restart services
restart:
	@echo " Restarting services..."
	@docker compose restart
	@echo " Services restarted"

# View logs
logs:
	@docker compose logs -f db

# Open PostgreSQL shell
db-shell:
	@docker compose exec db psql -U wingman -d ai_wingman

# Reset database (WARNING: deletes all data!)
db-reset:
	@echo "  WARNING: This will delete ALL database data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "  Resetting database..."
	@docker compose down -v
	@docker compose up -d
	@echo " Database reset complete"

# Run tests
test:
	@echo " Running tests..."
	@. venv/bin/activate && pytest tests/ -v

# Run linters
lint:
	@echo " Running linters..."
	@. venv/bin/activate && flake8 src/ tests/
	@. venv/bin/activate && mypy src/

# Format code
format:
	@echo " Formatting code..."
	@. venv/bin/activate && black src/ tests/ config/
	@echo " Code formatted"

# Clean generated files
clean:
	@echo " Cleaning generated files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete
	@echo " Cleaned"

# Clean everything (including venv and Docker volumes)
clean-all: clean
	@echo "  Removing virtual environment and database..."
	@rm -rf venv/
	@docker compose down -v
	@echo " Complete cleanup done"
