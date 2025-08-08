#!/bin/bash
# Script to pull models into Ollama containers

set -e

echo "🦙 Setting up Ollama models..."

# Function to pull model
pull_model() {
    local container_name=$1
    local model_name=$2
    local quant=${3:-"Q4_K_M"}
    
    echo "📥 Pulling ${model_name} into ${container_name}..."
    
    # Wait for container to be ready
    echo "⏳ Waiting for ${container_name} to be ready..."
    timeout 300 bash -c "until docker exec ${container_name} curl -f http://localhost:11434/api/tags > /dev/null 2>&1; do sleep 5; done"
    
    # Pull the model
    docker exec ${container_name} ollama pull ${model_name}
    
    echo "✅ ${model_name} ready in ${container_name}"
}

# Start containers if not running
echo "🚀 Starting Ollama containers..."
docker-compose up -d ollama-llama3 ollama-mistral ollama-codellama

# Pull models
pull_model "ollama-llama3" "llama3"
pull_model "ollama-mistral" "mistral"
pull_model "ollama-codellama" "codellama"

echo "🎉 All models are ready!"
echo ""
echo "Test your setup:"
echo "  curl http://localhost:11434/api/tags  # llama3"
echo "  curl http://localhost:11435/api/tags  # mistral"
echo "  curl http://localhost:11436/api/tags  # codellama"
