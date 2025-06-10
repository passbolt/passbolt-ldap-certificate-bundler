#!/bin/bash
# setup_python_env.sh - Sets up a Python virtual environment for the LDAPS Certificate Utility

set -e  # Exit immediately if a command exits with a non-zero status

echo "🔧 Checking for Python..."
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo "❌ Python 3 not found. Please install Python 3.6 or higher."
    exit 1
fi

# Check for pip and install if missing
PIP_PATH=$(which pip3)
if [ -z "$PIP_PATH" ]; then
    echo "📦 Pip not found. Attempting to install pip..."
    # Try using ensurepip first (works in most environments including Docker)
    if python3 -m ensurepip --version &> /dev/null; then
        python3 -m ensurepip --upgrade
        PIP_PATH=$(which pip3)
    # Fall back to package managers if ensurepip fails
    elif command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3-pip
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip
    elif command -v apk &> /dev/null; then
        sudo apk add --no-cache python3 py3-pip
    else
        echo "❌ Could not install pip automatically. Please install pip manually and try again."
        exit 1
    fi
    PIP_PATH=$(which pip3)
fi

echo "  • Python: $PYTHON_PATH"
echo "  • Pip:    $PIP_PATH"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "📦 Virtual environment already exists."
fi

# Install dependencies using the virtual environment's pip directly
echo "📄 Installing project dependencies..."
if ! venv/bin/pip install -q -r requirements.txt; then
    echo "❌ Failed to install dependencies. Please check your internet connection and try again."
    exit 1
fi
echo "  • Dependencies installed."

echo ""
echo "✅ Setup complete!"
echo ""
echo "👉 IMPORTANT: To use the tool, you need to activate the virtual environment in a new shell session:"
echo "   $ source venv/bin/activate"
echo ""
echo "   Then you can run the LDAPS certificate chain retriever:"
echo "   $ python ldaps_cert_chain_retriever.py --server <your-ldap-server> --port <your-ldap-port>"
echo ""
echo "   To leave the virtual environment when you're done, type: deactivate"
