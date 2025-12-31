#!/bin/bash
#
# API Governance Agent Installation Script
#
# Usage: curl -sL https://your-repo/install.sh | bash
#

set -e

echo "🚀 Installing API Governance Agent..."

# Detect OS
OS="$(uname -s)"
case "${OS}" in
  Linux*)     MACHINE=linux;;
  Darwin*)    MACHINE=mac;;
  *)          MACHINE="unknown:${OS}"
esac

if [ "$MACHINE" = "unknown:${OS}" ]; then
  echo "❌ Unsupported operating system: ${OS}"
  exit 1
fi

# Pull Docker image
echo "📦 Pulling Docker image..."
docker pull your-registry/api-governance:latest

# Create CLI alias
SHELL_RC=""
if [ -f "$HOME/.bashrc" ]; then
  SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
  SHELL_RC="$HOME/.zshrc"
fi

if [ -n "$SHELL_RC" ]; then
  echo "📝 Adding 'gov-check' alias to ${SHELL_RC}..."
  cat >> "$SHELL_RC" << 'EOF'

# API Governance Agent
alias gov-check='docker run --rm -v $(pwd):/project -e LLM_ENDPOINT=${LLM_ENDPOINT:-http://localhost:11434} your-registry/api-governance:latest'
EOF

  echo "✅ Installation complete!"
  echo "💡 Run 'source ${SHELL_RC}' or restart your terminal"
  echo "🎯 Usage: gov-check scan"
else
  echo "⚠️  Could not find shell config. Add alias manually:"
  echo "alias gov-check='docker run --rm -v \$(pwd):/project your-registry/api-governance:latest'"
fi
