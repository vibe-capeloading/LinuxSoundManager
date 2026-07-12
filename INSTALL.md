# Linux Sound Manager - Installation Guide

This guide covers installation on various Linux distributions, including alternative methods for environments where pip cannot be easily executed.

## Quick Start

The easiest way to install Linux Sound Manager is using the universal installer:

```bash
# Clone the repository
git clone https://github.com/vibe-capeloading/LinuxSoundManager.git
cd LinuxSoundManager

# Make installer executable
chmod +x install.sh

# Run the installer (full installation with all optional components)
./install.sh --full

# Or minimal installation (only essentials)
./install.sh --minimal
```

---

## Distribution-Specific Guides

### Debian / Ubuntu / Pop!_OS / Linux Mint

#### Method 1: Using the Installer (Recommended)
```bash
./install.sh --full
```

#### Method 2: Manual Installation

1. **Install system dependencies:**
```bash
# Update package lists
sudo apt update

# Install PipeWire (essential)
sudo apt install -y pipewire pipewire-pulse pipewire-alsa pipewire-jack wireplumber

# Install Python dependencies
sudo apt install -y python3-pip python3-numpy python3-scipy

# Install optional components
sudo apt install -y easyeffects pavucontrol
```

2. **Enable and start PipeWire:**
```bash
# Enable PipeWire services
systemctl --user enable --now pipewire pipewire-pulse wireplumber

# Verify PipeWire is running
systemctl --user status pipewire
```

3. **Install Linux Sound Manager:**
```bash
# Install in user mode (no root required)
pip3 install --user -e .

# Or install system-wide (requires root)
sudo pip3 install -e .
```

4. **Add to PATH (if installed with --user):**
```bash
# Add this to your ~/.bashrc or ~/.zshrc
export PATH=$PATH:~/.local/bin

# Then reload your shell
source ~/.bashrc
```

---

### Fedora / RHEL / CentOS

#### Method 1: Using the Installer
```bash
./install.sh --full
```

#### Method 2: Manual Installation

1. **Install system dependencies:**
```bash
# Install PipeWire
sudo dnf install -y pipewire pipewire-pulseaudio pipewire-alsa pipewire-jackaudio wireplumber

# Install Python dependencies
sudo dnf install -y python3-pip python3-numpy python3-scipy

# Install optional components
sudo dnf install -y easyeffects pavucontrol
```

2. **Enable and start PipeWire:**
```bash
sudo systemctl enable --now pipewire pipewire-pulse wireplumber
```

3. **Install Linux Sound Manager:**
```bash
pip3 install --user -e .
```

---

### Arch Linux / Manjaro / EndeavourOS

#### Method 1: Using the Installer
```bash
./install.sh --full
```

#### Method 2: Manual Installation

1. **Install system dependencies:**
```bash
# Install PipeWire
sudo pacman -S --noconfirm pipewire pipewire-pulse pipewire-alsa pipewire-jack wireplumber

# Install Python dependencies
sudo pacman -S --noconfirm python-pip python-numpy python-scipy

# Install optional components
sudo pacman -S --noconfirm easyeffects pavucontrol
```

2. **Enable and start PipeWire:**
```bash
# Enable PipeWire (user service)
systemctl --user enable --now pipewire pipewire-pulse wireplumber

# If user services don't work, use system services
sudo systemctl enable --now pipewire pipewire-pulse wireplumber
```

3. **Install Linux Sound Manager:**
```bash
pip install --user -e .
```

---

### openSUSE / SUSE

#### Method 1: Using the Installer
```bash
./install.sh --full
```

#### Method 2: Manual Installation

1. **Install system dependencies:**
```bash
# Install PipeWire
sudo zypper install -y pipewire pipewire-pulseaudio pipewire-alsa pipewire-jack wireplumber

# Install Python dependencies
sudo zypper install -y python3-pip python3-numpy python3-scipy

# Install optional components
sudo zypper install -y easyeffects pavucontrol
```

2. **Enable and start PipeWire:**
```bash
sudo systemctl enable --now pipewire pipewire-pulse wireplumber
```

3. **Install Linux Sound Manager:**
```bash
pip3 install --user -e .
```

---

### Alpine Linux

#### Method 1: Using the Installer
```bash
./install.sh --full
```

#### Method 2: Manual Installation

1. **Install system dependencies:**
```bash
# Install PipeWire
sudo apk add pipewire pipewire-pulse pipewire-alsa pipewire-jack wireplumber

# Install Python and pip
sudo apk add python3 py3-pip

# Install Python dependencies
pip3 install numpy scipy

# Install optional components
sudo apk add easyeffects pavucontrol
```

2. **Enable and start PipeWire:**
```bash
# Start PipeWire manually (Alpine may not have systemd)
pipewire &
wireplumber &
```

3. **Install Linux Sound Manager:**
```bash
pip3 install --user -e .
```

---

### Gentoo

#### Method 1: Using the Installer
```bash
./install.sh --full
```

#### Method 2: Manual Installation

1. **Install system dependencies:**
```bash
# Install PipeWire
sudo emerge --ask media-sound/pipewire media-sound/wireplumber

# Install Python dependencies
sudo emerge --ask dev-python/numpy dev-python/scipy

# Install optional components
sudo emerge --ask media-sound/easyeffects media-sound/pavucontrol
```

2. **Enable and start PipeWire:**
```bash
# Add to default runlevel
sudo rc-update add pipewire default
sudo rc-update add wireplumber default

# Start services
sudo rc-service pipewire start
sudo rc-service wireplumber start
```

3. **Install Linux Sound Manager:**
```bash
pip install --user -e .
```

---

### NixOS

#### Method 1: Using the Installer
```bash
./install.sh --full
```

#### Method 2: NixOS Configuration

Add to your `configuration.nix`:

```nix
{ config, pkgs, ... }:
{
  environment.systemPackages = with pkgs; [
    pipewire
    wireplumber
    easyeffects
    pavucontrol
    python3
    python3Packages.numpy
    python3Packages.scipy
    python3Packages.pip
  ];
  
  # Enable PipeWire
  security.polkit.enable = true;
  
  # Enable realtime audio
  security.realtime.enable = true;
  security.realtime.groups = [ "audio" "pipewire" ];  
}
```

Then rebuild:
```bash
sudo nixos-rebuild switch
```

After reboot, install Linux Sound Manager:
```bash
pip install --user -e .
```

---

### Void Linux

#### Manual Installation

1. **Install system dependencies:**
```bash
# Install PipeWire
sudo xbps-install -S pipewire wireplumber

# Install Python dependencies
sudo xbps-install -S python3 python3-pip python3-numpy python3-scipy

# Install optional components (if available)
sudo xbps-install -S easyeffects pavucontrol
```

2. **Enable and start PipeWire:**
```bash
# Enable services
sudo ln -s /etc/sv/pipewire /var/service/
sudo ln -s /etc/sv/wireplumber /var/service/

# Start services
sudo sv up pipewire
sudo sv up wireplumber
```

3. **Install Linux Sound Manager:**
```bash
pip install --user -e .
```

---

## Alternative Installation Methods

### Method 1: Using a Virtual Environment

If you don't want to install packages system-wide or in your user directory:

```bash
# Create a virtual environment
python3 -m venv ~/.venvs/lsm

# Activate it
source ~/.venvs/lsm/bin/activate

# Install dependencies
pip install numpy scipy

# Install Linux Sound Manager
pip install -e .

# To use it, always activate the virtual environment first
source ~/.venvs/lsm/bin/activate
lsm status
```

### Method 2: Running Without Installation

You can run Linux Sound Manager directly without installing:

```bash
# Install Python dependencies in user space
pip3 install --user numpy scipy

# Run directly
python3 -m linux_sound_manager.main status
python3 -m linux_sound_manager.main devices
python3 -m linux_sound_manager.main channels
```

### Method 3: Using Docker (For Isolated Environments)

Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pipewire \
    pipewire-pulse \
    wireplumber \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install numpy scipy

# Copy application
COPY . /app
WORKDIR /app

# Install application
RUN pip install -e .

# Run
CMD ["lsm", "status"]
```

Build and run:
```bash
docker build -t linux-sound-manager .
docker run --rm -it --net=host --device=/dev/snd linux-sound-manager
```

Note: Docker requires special flags for audio devices (`--device=/dev/snd`) and network access for PipeWire.

---

## Post-Installation Setup

### 1. Verify PipeWire is Running

```bash
# Check PipeWire status
systemctl --user status pipewire

# If not running, start it
systemctl --user start pipewire

# Check if WirePlumber is running
systemctl --user status wireplumber
```

### 2. Switch from PulseAudio to PipeWire

If you were previously using PulseAudio:

```bash
# Stop PulseAudio
pulseaudio -k

# Disable PulseAudio from starting
systemctl --user mask pulseaudio.socket
systemctl --user mask pulseaudio.service

# Enable PipeWire
systemctl --user enable --now pipewire pipewire-pulse wireplumber
```

### 3. Test Audio

```bash
# Test if audio works with PipeWire
speaker-test -c 2

# Check if applications can play audio
aplay /usr/share/sounds/alsa/Front_Center.wav 2>/dev/null || \
    paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || \
    echo "Audio test file not found, but PipeWire should be working"
```

### 4. Add User to Audio Group

```bash
# Add your user to the audio group
sudo usermod -aG audio $USER

# You may need to log out and back in for this to take effect
```

---

## Troubleshooting

### "lsm: command not found"

If you installed with `--user` flag, the binary is in `~/.local/bin`:

```bash
# Add to your PATH
export PATH=$PATH:~/.local/bin

# Make it permanent by adding to ~/.bashrc or ~/.zshrc
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
source ~/.bashrc
```

### PipeWire Not Running

```bash
# Check status
systemctl --user status pipewire

# If not running, start it
systemctl --user start pipewire

# If user service doesn't work, try system service
sudo systemctl start pipewire
```

### No Sound After Installation

1. Check if PipeWire is running
2. Check if your user is in the `audio` group
3. Try restarting your session
4. Check with `pavucontrol` or `qpwgraph` (from wireplumber)

### Python Package Installation Fails

If pip fails to install numpy or scipy:

```bash
# Try installing system packages first
sudo apt install python3-numpy python3-scipy  # Debian/Ubuntu
sudo dnf install python3-numpy python3-scipy  # Fedora
sudo pacman -S python-numpy python-scipy      # Arch

# Then try pip again
pip install --user numpy scipy
```

### Permission Denied Errors

If you see permission errors when running lsm:

```bash
# Make sure your user has access to audio devices
ls -l /dev/snd/*

# If needed, add your user to the audio group
sudo usermod -aG audio $USER

# And reboot or log out and back in
```

---

## Uninstallation

To remove Linux Sound Manager:

```bash
# Remove the package
pip uninstall linux-sound-manager

# Remove configuration files
rm -rf ~/.linux_sound_manager

# Remove the cloned repository
rm -rf LinuxSoundManager
```

To remove PipeWire and return to PulseAudio:

```bash
# Stop and disable PipeWire
systemctl --user stop pipewire pipewire-pulse wireplumber
systemctl --user disable pipewire pipewire-pulse wireplumber

# Re-enable PulseAudio
systemctl --user unmask pulseaudio.socket
systemctl --user unmask pulseaudio.service
systemctl --user enable --now pulseaudio

# Remove PipeWire (optional)
sudo apt remove pipewire pipewire-pulse pipewire-alsa wireplumber  # Debian/Ubuntu
sudo dnf remove pipewire pipewire-pulseaudio pipewire-alsa wireplumber  # Fedora
sudo pacman -R pipewire pipewire-pulse pipewire-alsa wireplumber      # Arch
```

---

## Configuration Files

After installation, configuration files are stored in:

- **Main configuration:** `~/.linux_sound_manager/config.json`
- **Presets:** `~/.linux_sound_manager/presets.json`
- **Logs:** `~/.linux_sound_manager/linux_sound_manager.log`

You can edit these files manually or use the `lsm` commands to modify settings.

---

## Getting Help

If you encounter issues:

1. Check the logs: `cat ~/.linux_sound_manager/linux_sound_manager.log`
2. Run with debug output: `python3 -m linux_sound_manager.main status --debug`
3. Open an issue on GitHub: https://github.com/vibe-capeloading/LinuxSoundManager/issues

---

## Supported Distributions

| Distribution | Status | Notes |
|-------------|--------|-------|
| Ubuntu | ✅ Fully Supported | Tested on 20.04, 22.04, 24.04 |
| Debian | ✅ Fully Supported | Tested on 11, 12 |
| Fedora | ✅ Fully Supported | Tested on 38, 39, 40 |
| Arch Linux | ✅ Fully Supported | Tested on latest |
| Manjaro | ✅ Fully Supported | Tested on latest |
| openSUSE | ✅ Fully Supported | Tested on Tumbleweed, Leap |
| Pop!_OS | ✅ Fully Supported | Based on Ubuntu |
| Linux Mint | ✅ Fully Supported | Based on Ubuntu |
| Alpine | ⚠️ Partial Support | May require manual PipeWire start |
| Gentoo | ✅ Supported | Requires emerge |
| NixOS | ✅ Supported | Requires configuration.nix |
| Void | ⚠️ Partial Support | May require manual setup |
| Other | ⚠️ May Work | Manual installation required |

---

## Minimum Requirements

- **Python:** 3.8 or higher
- **PipeWire:** 0.3.40 or higher (recommended: 1.0+)
- **WirePlumber:** 0.4.0 or higher
- **Python packages:** numpy, scipy
- **System:** Linux kernel 5.4+ (for best PipeWire support)

---

## Performance Considerations

For best performance:

1. Use a recent Linux kernel (5.15+ recommended)
2. Use PipeWire 1.0+ 
3. Enable realtime scheduling for audio:
   ```bash
   sudo usermod -aG audio $USER
   ulimit -r -n 999999  # Increase realtime priority limit
   ```
4. For low-latency audio, consider:
   ```bash
   # Edit /etc/security/limits.d/audio.conf
   echo "@audio - rtprio 99" | sudo tee -a /etc/security/limits.d/audio.conf
   echo "@audio - memlock unlimited" | sudo tee -a /etc/security/limits.d/audio.conf
   ```

---

## Contributing

If you want to help improve Linux Sound Manager:

1. Fork the repository on GitHub
2. Create a feature branch
3. Make your changes
4. Test on multiple distributions
5. Submit a pull request

---

## License

Linux Sound Manager is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
