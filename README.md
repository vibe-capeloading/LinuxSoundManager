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

## Requirements

- Python 3.8 or higher
- PipeWire (recommended) or PulseAudio
- EasyEffects (optional, for additional effects)

### Python Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install numpy scipy dbus-python pygobject
```

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/vibe-capeloading/LinuxSoundManager.git
cd LinuxSoundManager

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install .
```

### System Dependencies (Debian/Ubuntu)

```bash
# For PipeWire
sudo apt install pipewire pipewire-pulse pipewire-alsa pipewire-jack

# For EasyEffects (optional)
sudo apt install easyeffects

# For development
sudo apt install python3-dev python3-pip python3-venv
```

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
```

### Running as a Service

```bash
# Run in background
lsm --service

# Or use systemd (see systemd/ directory for service files)
```

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
    "game": {
      "volume": 1.0,
      "muted": false,
      "eq_enabled": true,
      "effects_enabled": true
    },
    "chat": {
      "volume": 1.0,
      "muted": false,
      "eq_enabled": true,
      "effects_enabled": true
    },
    "media": {
      "volume": 1.0,
      "muted": false,
      "eq_enabled": true,
      "effects_enabled": true
    },
    "aux": {
      "volume": 1.0,
      "muted": false,
      "eq_enabled": true,
      "effects_enabled": true
    },
    "microphone": {
      "volume": 1.0,
      "muted": false,
      "eq_enabled": true,
      "effects_enabled": true,
      "noise_gate_enabled": true,
      "compressor_enabled": true
    },
    "master": {
      "volume": 1.0,
      "muted": false
    }
  }
}
```

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

## Presets

Presets are stored in `~/.linux_sound_manager/presets.json`.

### Creating Custom Presets

```python
from linux_sound_manager.models.preset import Preset, EQBand, EQType

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

# Save the preset
config_manager = ConfigManager()
await config_manager.add_preset(preset)
```

## Troubleshooting

### PipeWire Not Running

```bash
# Start PipeWire
systemctl --user start pipewire pipewire-pulse

# Enable on startup
systemctl --user enable pipewire pipewire-pulse
```

### No Sound

1. Check if PipeWire is running: `systemctl --user status pipewire`
2. Check if applications are assigned to channels
3. Check channel volumes and mute states

### Permission Issues

Make sure your user is in the `audio` group:

```bash
sudo usermod -aG audio $USER
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests (if available)
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Inspired by SteelSeries Sonar
- Built on PipeWire and PulseAudio
- Uses EasyEffects for advanced audio processing
- Thanks to all contributors and the open-source community
