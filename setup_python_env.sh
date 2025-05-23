#!/bin/bash
# setup_python_env.sh - Sets up a Python virtual environment for the LDAPS Certificate Utility

set -e  # Exit immediately if a command exits with a non-zero status

echo "🔧 Checking for Python..."
PYTHON_PATH=$(which python3)
PIP_PATH=$(which pip)

echo "  • Python: $PYTHON_PATH"
echo "  • Pip:    $PIP_PATH"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "📦 Virtual environment already exists."
fi

# Activate the virtual environment
source venv/bin/activate
VENV_PYTHON=$(which python)
VENV_PIP=$(which pip)

echo "  • Virtual environment Python: $VENV_PYTHON"
echo "  • Virtual environment Pip:    $VENV_PIP"

# Install dependencies with quiet output
echo "📄 Installing project dependencies..."
pip install -q -r requirements.txt && echo "  • Dependencies installed."

echo ""
echo "✅ Setup complete."
echo ""
echo "👉 Now activate the Python virtual environment:"
echo "   $ source venv/bin/activate"
echo "   run the LDAPS certificate chain retriever with:"
echo "   $ python ldaps_cert_chain_retriever.py --server <your-ldap-server> --port <your-ldap-port>"
echo ""
echo "   To leave it, type: deactivate"
