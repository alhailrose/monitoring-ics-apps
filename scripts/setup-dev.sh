#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Monitoring Hub Dev Environment Setup ===${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Docker Compose not found. Please install Docker Compose first.${NC}"
    exit 1
fi

cd "$(dirname "$0")"

echo -e "\n${YELLOW}Starting PostgreSQL and Ollama...${NC}"
docker compose -f docker-compose.dev.yml up -d postgres ollama

echo -e "\n${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
until docker exec monitoring-postgres pg_isready -U postgres &> /dev/null; do
    echo -n "."
    sleep 1
done
echo -e " ${GREEN}Ready!${NC}"

echo -e "\n${YELLOW}Waiting for Ollama to be ready...${NC}"
until curl -s http://localhost:11434/api/tags &> /dev/null; do
    echo -n "."
    sleep 1
done
echo -e " ${GREEN}Ready!${NC}"

# Check if model exists
echo -e "\n${YELLOW}Checking for llama3.2 model...${NC}"
if ! curl -s http://localhost:11434/api/tags | grep -q "llama3.2"; then
    echo -e "${YELLOW}Pulling llama3.2 model (this may take a few minutes)...${NC}"
    docker exec monitoring-ollama ollama pull llama3.2
fi
echo -e "${GREEN}Model ready!${NC}"

# Setup Python env if needed
echo -e "\n${YELLOW}Setting up Python environment...${NC}"
cd backend

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

# Initialize database
echo -e "\n${YELLOW}Initializing database...${NC}"
python -c "from app.core.database import init_db; init_db(); print('Database initialized!')"

echo -e "\n${GREEN}=== Setup Complete! ===${NC}"
echo -e "\nServices running:"
echo -e "  - PostgreSQL: localhost:5432"
echo -e "  - Ollama:     localhost:11434"
echo -e "\nTo start the backend:"
echo -e "  cd backend && source .venv/bin/activate"
echo -e "  uvicorn app.main:app --reload --port 8000"
echo -e "\nAPI docs: http://localhost:8000/docs"
