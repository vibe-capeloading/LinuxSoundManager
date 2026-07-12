#!/bin/bash

# Linux Sound Manager - Dependency Checker
# This script checks if all required dependencies are installed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Linux Sound Manager - Dependency Check${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

function print_check() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

function print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

function print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

function check_command() {
    command -v "$1" >/dev/null 2>&1
    return $?
}

function check_python_module() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

function check_pipewire() {
    print_info "Checking PipeWire..."
    
    local missing=0
    
    # Check PipeWire
    if check_command pipewire; then
        print_check 0 "PipeWire is installed"
    else
        print_check 1 "PipeWire is NOT installed"
        missing=$((missing + 1))
    fi
    
    # Check WirePlumber
    if check_command wireplumber; then
        print_check 0 "WirePlumber is installed"
    else
        print_check 1 "WirePlumber is NOT installed"
        missing=$((missing + 1))
    fi
    
    # Check if PipeWire is running
    if pgrep -x pipewire >/dev/null 2>&1; then
        print_check 0 "PipeWire is running"
    else
        print_warning "PipeWire is installed but not running"
        print_info "  Start with: systemctl --user start pipewire"
    fi
    
    # Check if WirePlumber is running
    if pgrep -x wireplumber >/dev/null 2>&1; then
        print_check 0 "WirePlumber is running"
    else
        print_warning "WirePlumber is installed but not running"
        print_info "  Start with: systemctl --user start wireplumber"
    fi
    
    return $missing
}

function check_python() {
    print_info "Checking Python..."
    
    local missing=0
    
    # Check Python 3
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
        print_check 0 "Python 3 is installed (version: $PYTHON_VERSION)"
        
        # Check Python version
        if [[ "$PYTHON_VERSION" > "3.8" ]]; then
            print_check 0 "Python version is >= 3.8"
        else
            print_check 1 "Python version is < 3.8 (required: >= 3.8)"
            missing=$((missing + 1))
        fi
    else
        print_check 1 "Python 3 is NOT installed"
        missing=$((missing + 1))
    fi
    
    # Check pip
    if check_command pip3; then
        print_check 0 "pip3 is installed"
    else
        print_check 1 "pip3 is NOT installed"
        missing=$((missing + 1))
    fi
    
    return $missing
}

function check_python_packages() {
    print_info "Checking Python packages..."
    
    local missing=0
    
    # Check numpy
    if check_python_module numpy; then
        print_check 0 "numpy is installed"
    else
        print_check 1 "numpy is NOT installed"
        missing=$((missing + 1))
    fi
    
    # Check scipy
    if check_python_module scipy; then
        print_check 0 "scipy is installed"
    else
        print_check 1 "scipy is NOT installed"
        missing=$((missing + 1))
    fi
    
    return $missing
}

function check_optional() {
    print_info "Checking optional dependencies..."
    
    local missing=0
    
    # Check EasyEffects
    if check_command easyeffects; then
        print_check 0 "EasyEffects is installed (optional)"
    else
        print_check 1 "EasyEffects is NOT installed (optional)"
        print_info "  Install for additional audio effects"
    fi
    
    # Check pavucontrol
    if check_command pavucontrol; then
        print_check 0 "pavucontrol is installed (optional)"
    else
        print_check 1 "pavucontrol is NOT installed (optional)"
        print_info "  Install for GUI audio control"
    fi
    
    return 0  # Optional packages don't count as missing
}

function check_user_groups() {
    print_info "Checking user permissions..."
    
    local missing=0
    
    # Check if user is in audio group
    if groups $(whoami) 2>/dev/null | grep -qw audio; then
        print_check 0 "User is in 'audio' group"
    else
        print_check 1 "User is NOT in 'audio' group"
        print_info "  Add with: sudo usermod -aG audio $(whoami)"
        missing=$((missing + 1))
    fi
    
    return $missing
}

function show_installation_commands() {
    echo
    print_header
    echo -e "${YELLOW}Installation Commands for Your System${NC}"
    echo
    
    DISTRO="unknown"
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO="$ID"
    elif check_command lsb_release; then
        DISTRO=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
    fi
    
    case $DISTRO in
        ubuntu|debian|pop|linuxmint)
            echo "Debian/Ubuntu-based system detected:"
            echo "  sudo apt update"
            echo "  sudo apt install -y pipewire pipewire-pulse pipewire-alsa wireplumber python3-pip python3-numpy python3-scipy"
            echo "  pip3 install --user -e ."
            echo "  systemctl --user enable --now pipewire pipewire-pulse wireplumber"
            ;;
        fedora|rhel|centos)
            echo "Fedora/RHEL-based system detected:"
            echo "  sudo dnf install -y pipewire pipewire-pulseaudio pipewire-alsa wireplumber python3-pip python3-numpy python3-scipy"
            echo "  pip3 install --user -e ."
            echo "  sudo systemctl enable --now pipewire pipewire-pulse wireplumber"
            ;;
        arch|manjaro|endeavouros)
            echo "Arch Linux-based system detected:"
            echo "  sudo pacman -S --noconfirm pipewire pipewire-pulse pipewire-alsa wireplumber python-pip python-numpy python-scipy"
            echo "  pip install --user -e ."
            echo "  systemctl --user enable --now pipewire pipewire-pulse wireplumber"
            ;;
        opensuse|suse)
            echo "openSUSE system detected:"
            echo "  sudo zypper install -y pipewire pipewire-pulseaudio pipewire-alsa wireplumber python3-pip python3-numpy python3-scipy"
            echo "  pip3 install --user -e ."
            echo "  sudo systemctl enable --now pipewire pipewire-pulse wireplumber"
            ;;
        alpine)
            echo "Alpine Linux detected:"
            echo "  sudo apk add pipewire pipewire-pulse pipewire-alsa wireplumber python3 py3-pip"
            echo "  pip3 install numpy scipy"
            echo "  pip3 install --user -e ."
            echo "  pipewire & wireplumber &"
            ;;
        *)
            echo "Unknown system detected. Using universal commands:"
            echo "  ./install.sh --full"
            ;;
    esac
    
    echo
}

# Main function
function main() {
    print_header
    
    local total_missing=0
    
    # Check PipeWire
    pipewire_missing=$(check_pipewire)
    total_missing=$((total_missing + pipewire_missing))
    echo
    
    # Check Python
    python_missing=$(check_python)
    total_missing=$((total_missing + python_missing))
    echo
    
    # Check Python packages
    packages_missing=$(check_python_packages)
    total_missing=$((total_missing + packages_missing))
    echo
    
    # Check optional
    check_optional
    echo
    
    # Check user groups
    groups_missing=$(check_user_groups)
    total_missing=$((total_missing + groups_missing))
    echo
    
    # Summary
    print_header
    echo -e "${BLUE}Summary${NC}"
    echo
    
    if [ $total_missing -eq 0 ]; then
        echo -e "${GREEN}All required dependencies are installed!${NC}"
        echo
        echo -e "You can now run Linux Sound Manager:"
        echo -e "  lsm status"
        echo -e "  python3 -m linux_sound_manager.main status"
    else
        echo -e "${RED}Missing $total_missing required dependency/dependencies${NC}"
        echo
        show_installation_commands
    fi
    
    exit $total_missing
}

# Run main function
main "$@"
