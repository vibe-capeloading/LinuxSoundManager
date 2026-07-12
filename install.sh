#!/bin/bash

# Linux Sound Manager - Universal Installer
# This script handles installation on various Linux distributions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
function print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Linux Sound Manager Installer${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

function print_step() {
    echo -e "${YELLOW}→${NC} $1"
}

function print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

function print_error() {
    echo -e "${RED}✗${NC} $1"
}

function print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

function check_command() {
    command -v "$1" >/dev/null 2>&1
}

function detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO="$ID"
        VERSION="$VERSION_ID"
    elif check_command lsb_release; then
        DISTRO=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        VERSION=$(lsb_release -sr)
    elif [ -f /etc/redhat-release ]; then
        DISTRO="redhat"
    else
        DISTRO="unknown"
    fi
    echo "$DISTRO"
}

function install_python_packages() {
    print_step "Installing Python packages..."
    
    # Check if pip is available
    if check_command pip3; then
        PIP_CMD="pip3"
    elif check_command pip; then
        PIP_CMD="pip"
    else
        print_error "pip is not installed. Trying to install pip first..."
        install_pip
        PIP_CMD="pip3"
    fi
    
    # Install required Python packages
    $PIP_CMD install --user numpy scipy 2>/dev/null || {
        print_error "Failed to install Python packages with pip"
        print_info "Trying alternative installation methods..."
        
        # Try with apt
        if check_command apt-get; then
            sudo apt-get update && sudo apt-get install -y python3-numpy python3-scipy
        # Try with dnf
        elif check_command dnf; then
            sudo dnf install -y python3-numpy python3-scipy
        # Try with pacman
        elif check_command pacman; then
            sudo pacman -S --noconfirm python-numpy python-scipy
        # Try with zypper
        elif check_command zypper; then
            sudo zypper install -y python3-numpy python3-scipy
        else
            print_error "Cannot install Python packages. Please install numpy and scipy manually."
            print_info "Required packages: numpy, scipy"
            exit 1
        fi
    }
    
    print_success "Python packages installed"
}

function install_pip() {
    print_step "Installing pip..."
    
    if check_command apt-get; then
        sudo apt-get update && sudo apt-get install -y python3-pip
    elif check_command dnf; then
        sudo dnf install -y python3-pip
    elif check_command pacman; then
        sudo pacman -S --noconfirm python-pip
    elif check_command zypper; then
        sudo zypper install -y python3-pip
    elif check_command apk; then
        sudo apk add py3-pip
    else
        print_error "Cannot install pip automatically"
        print_info "Please install pip manually: https://pip.pypa.io/en/stable/installation/"
        exit 1
    fi
    
    print_success "pip installed"
}

function install_pipewire() {
    print_step "Installing PipeWire..."
    
    DISTRO=$(detect_distro)
    
    case $DISTRO in
        ubuntu|debian|pop|linuxmint)
            sudo apt-get update
            sudo apt-get install -y pipewire pipewire-pulse pipewire-alsa pipewire-jack wireplumber
            ;;
        fedora|rhel|centos)
            sudo dnf install -y pipewire pipewire-pulseaudio pipewire-alsa pipewire-jackaudio wireplumber
            ;;
        arch|cachyos|manjaro|endeavouros)
            sudo pacman -S --noconfirm pipewire pipewire-pulse pipewire-alsa pipewire-jack wireplumber
            ;;
        opensuse|suse)
            sudo zypper install -y pipewire pipewire-pulseaudio pipewire-alsa pipewire-jack wireplumber
            ;;
        alpine)
            sudo apk add pipewire pipewire-pulse pipewire-alsa pipewire-jack wireplumber
            ;;
        gentoo)
            sudo emerge --ask media-sound/pipewire media-sound/wireplumber
            ;;
        nixos)
            print_info "On NixOS, add to configuration.nix:"
            print_info "  environment.systemPackages = [ pkgs.pipewire pkgs.wireplumber ];"
            print_info "  security.polkit.enable = true;"
            print_info "Then run: sudo nixos-rebuild switch"
            exit 0
            ;;
        *)
            print_error "Unsupported distribution for automatic PipeWire installation"
            print_info "Please install PipeWire manually:"
            print_info "  - PipeWire: https://pipewire.pages.freedesktop.org/wireplumber/"
            print_info "  - Required packages: pipewire, pipewire-pulse, pipewire-alsa, wireplumber"
            exit 1
            ;;
    esac
    
    # Enable and start PipeWire
    print_step "Enabling PipeWire services..."
    
    if check_command systemctl; then
        # User service
        systemctl --user enable --now pipewire pipewire-pulse wireplumber 2>/dev/null || \
        sudo systemctl enable --now pipewire pipewire-pulse wireplumber
    else
        print_info "systemctl not available, you may need to start PipeWire manually:"
        print_info "  pipewire &"
        print_info "  wireplumber &"
    fi
    
    print_success "PipeWire installed and enabled"
}

function install_easyeffects() {
    print_step "Installing EasyEffects (optional)..."
    
    DISTRO=$(detect_distro)
    
    case $DISTRO in
        ubuntu|debian|pop|linuxmint)
            # Add repository for newer versions
            if ! grep -q "easyeffects" /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null; then
                sudo add-apt-repository -y ppa:mikhailnov/pulseeffects
                sudo apt-get update
            fi
            sudo apt-get install -y easyeffects
            ;;
        fedora|rhel|centos)
            sudo dnf install -y easyeffects
            ;;
        arch|manjaro|endeavouros)
            sudo pacman -S --noconfirm easyeffects
            ;;
        opensuse|suse)
            sudo zypper install -y easyeffects
            ;;
        *)
            print_info "EasyEffects not available in official repositories for your distribution"
            print_info "You can build from source: https://github.com/wwmm/easyeffects"
            ;;
    esac
    
    print_success "EasyEffects installation attempted"
}

function install_pavucontrol() {
    print_step "Installing pavucontrol (optional)..."
    
    DISTRO=$(detect_distro)
    
    case $DISTRO in
        ubuntu|debian|pop|linuxmint)
            sudo apt-get install -y pavucontrol
            ;;
        fedora|rhel|centos)
            sudo dnf install -y pavucontrol
            ;;
        arch|manjaro|endeavouros)
            sudo pacman -S --noconfirm pavucontrol
            ;;
        opensuse|suse)
            sudo zypper install -y pavucontrol
            ;;
        alpine)
            sudo apk add pavucontrol
            ;;
        *)
            print_info "pavucontrol not available for your distribution"
            ;;
    esac
    
    print_success "pavucontrol installation attempted"
}

function install_lsm() {
    print_step "Installing Linux Sound Manager..."
    
    # Create config directory
    mkdir -p ~/.linux_sound_manager
    
    # Install using pip in user mode
    if check_command pip3; then
        pip3 install --user -e . 2>/dev/null || {
            print_info "Trying alternative installation..."
            python3 -m pip install --user -e .
        }
    else
        print_error "pip is required to install Linux Sound Manager"
        exit 1
    fi
    
    print_success "Linux Sound Manager installed"
}

function verify_installation() {
    print_step "Verifying installation..."
    
    # Check if lsm command works
    if command -v lsm >/dev/null 2>&1; then
        print_success "lsm command is available"
        lsm status 2>&1 | head -5 || true
    else
        print_info "lsm command not in PATH"
        print_info "You can run it directly with: python3 -m linux_sound_manager.main"
    fi
    
    # Check PipeWire
    if check_command pipewire; then
        print_success "PipeWire is installed"
        if pgrep -x pipewire >/dev/null 2>&1; then
            print_success "PipeWire is running"
        else
            print_info "PipeWire is not running. Start it with: systemctl --user start pipewire"
        fi
    else
        print_error "PipeWire is not installed"
    fi
}

function show_usage() {
    print_header
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  --full          Install all components including optional ones"
    echo "  --minimal      Install only required components"
    echo "  --help, -h     Show this help message"
    echo
    echo "Examples:"
    echo "  $0                    # Interactive installation"
    echo "  $0 --full             # Install everything"
    echo "  $0 --minimal          # Install only essentials"
    echo
}

# Main installation
function main() {
    print_header
    
    # Parse arguments
    FULL_INSTALL=false
    MINIMAL_INSTALL=false
    
    for arg in "$@"; do
        case $arg in
            --full)
                FULL_INSTALL=true
                ;;
            --minimal)
                MINIMAL_INSTALL=true
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
        esac
    done
    
    # Check if we're in the right directory
    if [ ! -f "setup.py" ]; then
        print_error "Please run this script from the LinuxSoundManager directory"
        print_info "cd /path/to/LinuxSoundManager && ./install.sh"
        exit 1
    fi
    
    # Detect distribution
    DISTRO=$(detect_distro)
    print_info "Detected distribution: $DISTRO"
    echo
    
    # Install Python packages
    install_python_packages
    echo
    
    # Install PipeWire (essential)
    install_pipewire
    echo
    
    # Install optional components
    if [ "$MINIMAL_INSTALL" = false ]; then
        if [ "$FULL_INSTALL" = true ] || [ "$DISTRO" != "nixos" ]; then
            install_easyeffects
            echo
        fi
        
        install_pavucontrol
        echo
    fi
    
    # Install LSM
    install_lsm
    echo
    
    # Verify
    verify_installation
    echo
    
    print_header
    print_success "Installation completed!"
    echo
    print_info "To start using Linux Sound Manager:"
    print_info "  1. Make sure PipeWire is running: systemctl --user status pipewire"
    print_info "  2. Run: lsm status"
    print_info "  3. Or run: python3 -m linux_sound_manager.main status"
    echo
    print_info "For more commands, run: lsm --help"
    echo
}

# Run main function
main "$@"
