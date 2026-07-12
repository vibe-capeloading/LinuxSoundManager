# Linux Sound Manager

A SteelSeries Sonar-like audio mixer for Linux, providing advanced audio routing, effects, and mixing capabilities.

## Features

- **5 Audio Channels**: Game, Chat, Media, Aux, and Microphone
- **Virtual Audio Devices**: Creates virtual sinks/sources for each channel using PipeWire
- **Advanced Mixing**: Route audio between channels with volume and pan control
- **Parametric EQ**: 10-band parametric equalizer per channel
- **Audio Effects**:
  - Noise Gate
  - Compressor
  - Limiter
  - ClearCast AI noise suppression (via RNNoise)
- **Spatial Audio**: 360-degree audio simulation with HRTF
- **Presets**: Save and load EQ and effect configurations
- **EasyEffects Integration**: Optional integration with EasyEffects for additional effects
- **Pavucontrol Integration**: Compatible with existing PulseAudio/PipeWire tools

## Quick Start

The easiest way to get started is with our universal installer:

```bash
# Clone the repository
git clone https://github.com/vibe-capeloading/LinuxSoundManager.git
cd LinuxSoundManager

# Make installer executable
chmod +x install.sh

# Run the installer (full installation)
./install.sh --full

# Or minimal installation (only essentials)
./install.sh --minimal
```

That's it! The installer will automatically detect your distribution and install all required dependencies.

---

## Detailed Installation

For detailed installation instructions for specific distributions, see our [Installation Guide](INSTALL.md).

### Supported Installation Methods:

| Method | Description | Command |
|--------|-------------|---------|
| **Universal Installer** | Recommended for most users | `./install.sh --full` |
| **Manual pip** | For users who prefer pip | `pip install -e .` |
| **Virtual Environment** | Isolated Python environment | See below |
| **Docker** | Containerized installation | See below |
| **Package Managers** | Distribution-specific packages | See INSTALL.md |

### Manual Installation with pip

If you prefer to install manually:

```bash
# Clone the repository
git clone https://github.com/vibe-capeloading/LinuxSoundManager.git
cd LinuxSoundManager

# Install Python dependencies
pip install --user numpy scipy

# Install the package
pip install --user -e .
```

### Using a Virtual Environment

For a clean, isolated installation:

```bash
# Create virtual environment
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

### Using Docker

For isolated environments or easy deployment:

```bash
# Build the image
docker build -t linux-sound-manager .

# Run with audio device access
docker run --rm -it \
  --net=host \
  --device=/dev/snd \
  -e PULSE_SERVER=unix:/run/user/$(id -u)/pulse/native \
  linux-sound-manager
```

---

## Requirements

### System Requirements

- **Linux Distribution**: Most modern distributions (see [Installation Guide](INSTALL.md) for full list)
- **Python**: 3.8 or higher
- **PipeWire**: 0.3.40+ (recommended: 1.0+)
- **WirePlumber**: 0.4.0+

### Python Dependencies

- numpy (>= 1.20.0)
- scipy (>= 1.7.0)

Optional:
- dbus-python (for D-Bus integration)
- pygobject (for GTK integration, future UI)

### System Dependencies

- PipeWire
- WirePlumber
- ALSA (for compatibility)

Optional:
- EasyEffects (for additional audio effects)
- pavucontrol (for GUI audio control)

---

## Usage

### Command Line Interface

```bash
# Show application status
lsm status

# List audio devices
lsm devices

# List audio sources (applications)
lsm sources

# List channels
lsm channels

# List presets
lsm presets

# Set channel volume (0.0 to 1.0)
lsm set-volume game 0.8

# Mute/unmute channel
lsm set-mute chat true

# Set master volume
lsm set-master-volume 0.5

# Assign application to channel
lsm assign firefox media

# Apply preset
lsm apply gaming

# Show help
lsm --help
```

### Running as a Service

```bash
# Run in background
lsm --service

# Or use systemd (see systemd/ directory for service files)
systemctl --user enable --now linux-sound-manager
```

---

## Distribution Support

Linux Sound Manager is tested and supported on the following distributions:

| Distribution | Status | Installation Method |
|-------------|--------|-------------------|
| **Ubuntu** | ✅ Fully Supported | `./install.sh --full` |
| **Debian** | ✅ Fully Supported | `./install.sh --full` |
| **Fedora** | ✅ Fully Supported | `./install.sh --full` |
| **Arch Linux** | ✅ Fully Supported | `./install.sh --full` or PKGBUILD |
| **Manjaro** | ✅ Fully Supported | `./install.sh --full` |
| **openSUSE** | ✅ Fully Supported | `./install.sh --full` |
| **Pop!_OS** | ✅ Fully Supported | `./install.sh --full` |
| **Linux Mint** | ✅ Fully Supported | `./install.sh --full` |
| **Alpine** | ⚠️ Partial Support | Manual setup required |
| **Gentoo** | ✅ Supported | `./install.sh --full` or emerge |
| **NixOS** | ✅ Supported | Configuration.nix |
| **Void** | ⚠️ Partial Support | Manual setup required |

For detailed instructions for each distribution, see our [Installation Guide](INSTALL.md).

---

## Configuration

Configuration is stored in `~/.linux_sound_manager/config.json`.

### Default Configuration

```json
{
  "version": "1.0",
  "audio_engine": {
    "sample_rate": 48000,
    "buffer_size": 1024,
    "latency": 0.01,
    "enable_spatial": false,
    "enable_effects": true,
    "enable_eq": true
  },
  "channels": {
    "game": {"volume": 1.0, "muted": false, "eq_enabled": true, "effects_enabled": true},
    "chat": {"volume": 1.0, "muted": false, "eq_enabled": true, "effects_enabled": true},
    "media": {"volume": 1.0, "muted": false, "eq_enabled": true, "effects_enabled": true},
    "aux": {"volume": 1.0, "muted": false, "eq_enabled": true, "effects_enabled": true},
    "microphone": {"volume": 1.0, "muted": false, "eq_enabled": true, "effects_enabled": true, "noise_gate_enabled": true, "compressor_enabled": true},
    "master": {"volume": 1.0, "muted": false}
  }
}
```

---

## Presets

Presets are stored in `~/.linux_sound_manager/presets.json`.

### Creating Custom Presets

```python
from linux_sound_manager.models.preset import Preset, EQBand, EQType, PresetType

# Create a custom EQ preset
preset = Preset(
    name="My Custom EQ",
    description="Custom EQ for gaming",
    preset_type=PresetType.EQ,
    eq_bands=[
        EQBand(frequency=60, gain=2.0, q_factor=1.2, eq_type=EQType.PEAKING),
        EQBand(frequency=250, gain=1.5, q_factor=1.0, eq_type=EQType.PEAKING),
        EQBand(frequency=1000, gain=0.0, q_factor=1.0, eq_type=EQType.PEAKING),
        EQBand(frequency=4000, gain=-1.0, q_factor=1.0, eq_type=EQType.PEAKING),
        EQBand(frequency=16000, gain=-2.0, q_factor=0.8, eq_type=EQType.PEAKING),
    ]
)
```

---

## Troubleshooting

### "lsm: command not found"

If you installed with `--user` flag, the binary is in `~/.local/bin`:

```bash
# Add to your PATH
export PATH=$PATH:~/.local/bin

# Make it permanent
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
source ~/.bashrc
```

### PipeWire Not Running

```bash
# Check status
systemctl --user status pipewire

# If not running, start it
systemctl --user start pipewire
```

### No Sound After Installation

1. Check if PipeWire is running
2. Check if your user is in the `audio` group
3. Try restarting your session
4. Check with `pavucontrol` or `qpwgraph`

### Check Dependencies

Run our dependency checker:

```bash
chmod +x check_dependencies.sh
./check_dependencies.sh
```

This will show you exactly what's missing and how to install it.

---

## Architecture

### Core Components

1. **AudioEngine**: Main audio processing engine
2. **PipeWireManager**: Low-level PipeWire integration
3. **ChannelManager**: Manages the 5 audio channels
4. **AudioMixer**: Handles audio mixing and routing
5. **EffectsManager**: Manages EQ, noise gate, compressor, etc.
6. **SpatialAudio**: 360-degree audio simulation

### Services

1. **EasyEffectsIntegration**: Integration with EasyEffects
2. **PavucontrolIntegration**: Integration with pavucontrol

### Models

1. **AudioDevice**: Represents audio devices
2. **AudioSource**: Represents audio sources (applications)
3. **Preset**: EQ and effect presets

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python3 test_engine.py`
5. Submit a pull request

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Inspired by SteelSeries Sonar
- Built on PipeWire and PulseAudio
- Uses EasyEffects for advanced audio processing
- Thanks to all contributors and the open-source community

---

## Additional Resources

- [Installation Guide](INSTALL.md) - Detailed installation for all distributions
- [GitHub Repository](https://github.com/vibe-capeloading/LinuxSoundManager) - Source code and issues
- [PipeWire Documentation](https://pipewire.pages.freedesktop.org/wireplumber/) - PipeWire official docs
- [EasyEffects](https://github.com/wwmm/easyeffects) - Advanced audio effects
