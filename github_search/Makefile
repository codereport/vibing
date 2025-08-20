# GitHub Thrust Search Tool - Makefile

.PHONY: help install install-pip install-dev update run test docker clean lint setup activate

# Default target
help:
	@echo "GitHub Thrust Search Tool"
	@echo "Available commands:"
	@echo "  install       - Install Python dependencies with uv"
	@echo "  install-pip   - Install Python dependencies with pip (fallback)"
	@echo "  install-dev   - Install with development dependencies"
	@echo "  update        - Update all dependencies"
	@echo "  run           - Start the web application"
	@echo "  test          - Run test suite"
	@echo "  activate      - Show how to activate virtual environment"
	@echo "  docker        - Build and run with Docker"
	@echo "  clean         - Clean up temporary files"
	@echo "  lint          - Run code linting"
	@echo ""
	@echo "Setup:"
	@echo "  1. Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
	@echo "  2. Create .env file with GITHUB_TOKEN=your_token"
	@echo "  3. Run 'make install' to install dependencies"
	@echo "  4. Run 'make run' to start the application"

# Install dependencies with uv
install:
	@echo "📦 Installing dependencies with uv..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		uv venv; \
	fi
	uv pip install -r requirements.txt
	@echo "✅ Dependencies installed!"
	@echo "💡 To activate the virtual environment, run: source .venv/bin/activate"

# Install dependencies with pip (fallback)
install-pip:
	@echo "📦 Installing dependencies with pip..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed!"

# Update dependencies
update:
	@echo "🔄 Updating dependencies..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		uv venv; \
	fi
	uv pip install --upgrade -r requirements.txt
	@echo "✅ Dependencies updated!"

# Install development dependencies
install-dev: install
	@echo "📦 Installing dev dependencies..."
	uv pip install pytest>=7.0.0 pytest-asyncio>=0.21.0 black>=23.0.0 ruff>=0.1.0
	@echo "✅ Dev dependencies installed!"

# Run the application
run:
	@echo "🚀 Starting GitHub Thrust Search Tool..."
	@if [ -d ".venv" ]; then \
		.venv/bin/python run.py; \
	else \
		python run.py; \
	fi

# Activate virtual environment (for manual use)
activate:
	@echo "To activate the virtual environment, run:"
	@echo "source .venv/bin/activate"

# Run tests
test:
	@echo "🧪 Running test suite..."
	@if [ -d ".venv" ]; then \
		.venv/bin/python test_search.py; \
	else \
		python test_search.py; \
	fi

# Docker build and run
docker:
	@echo "🐳 Building Docker image..."
	docker-compose up --build

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	@echo "✅ Cleanup complete!"

# Lint code (if flake8 is installed)
lint:
	@echo "🔍 Running code linting..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 *.py --max-line-length=100 --ignore=E501,W503; \
	else \
		echo "flake8 not installed, skipping lint"; \
	fi

# Quick setup for new users
setup: install
	@echo ""
	@echo "🎯 Quick Setup Complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Create a .env file with your GitHub token:"
	@echo "   echo 'GITHUB_TOKEN=your_token_here' > .env"
	@echo ""
	@echo "2. Start the application:"
	@echo "   make run"
	@echo ""
	@echo "3. Open http://localhost:8000 in your browser"
	@echo ""
	@echo "📚 For development:"
	@echo "   make install-dev  # Install with dev dependencies"
	@echo "   make update       # Update all dependencies"
