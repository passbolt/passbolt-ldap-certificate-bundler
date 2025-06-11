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

# Check that venv module is available
echo "🔍 Checking for venv support..."
if ! python3 -m venv --help > /dev/null 2>&1; then
    echo "❌ Python venv module not available."
    echo "   On Debian/Ubuntu, run: sudo apt-get install python3-venv"
    echo "   Then re-run this setup script."
    exit 1
fi

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
    echo "❌ Failed to install dependencies."
    echo "   If you see cryptography build errors, ensure you have system dependencies installed:"
    echo "   Debian/Ubuntu: sudo apt-get install build-essential libssl-dev libffi-dev python3-dev"
    echo "   Then try re-running this script."
exit 1

    exit 1
fi
echo "  • Dependencies installed."

echo ""
echo "✅ Setup complete!"
echo ""
echo "👉 To use the tool, activate the virtual environment in your shell (this script does not keep it activated):"
echo "   $ source venv/bin/activate"
echo ""
echo "   Then you can run the LDAPS certificate chain retriever:"
echo "   $ python ldaps_cert_chain_retriever.py --server <your-ldap-server> --port <your-ldap-port>"
echo ""
echo "   To leave the virtual environment when you're done, type:"
echo "   $ deactivate"
echo ""
echo "👉 To re-activate any python virtual environment when you're in its directory, type:"
echo "   $ source venv/bin/activate"
echo ""
echo "   The python files, libraries, and dependencies are now installed in the venv directory."
echo "   You can delete the venv directory when you're done with the tool or if you want to use it on another machine"
echo "   with a different version of python."
