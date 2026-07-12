#!/usr/bin/env python3
"""
Test script for Linux Sound Manager

This script tests the core functionality of the audio engine.
"""

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from linux_sound_manager.core.audio_engine import AudioEngine, EngineState
from linux_sound_manager.core.channels import ChannelType
from linux_sound_manager.models.preset import Preset, PresetType


async def test_initialization():
    """Test engine initialization"""
    print("Testing engine initialization...")
    
    engine = AudioEngine()
    success = await engine.initialize()
    
    if success:
        print("✓ Engine initialized successfully")
        state = await engine.get_state()
        print(f"  Engine state: {state.name}")
        return engine
    else:
        print("✗ Failed to initialize engine")
        return None


async def test_channels(engine: AudioEngine):
    """Test channel management"""
    print("\nTesting channel management...")
    
    channels = await engine.get_channels()
    print(f"  Found {len(channels)} channels")
    
    for channel in channels:
        print(f"    - {channel.name}: Volume={channel.settings.volume:.2f}, Muted={channel.settings.muted}")
    
    # Test setting channel volume
    success = await engine.set_channel_volume(ChannelType.GAME, 0.8)
    if success:
        print("✓ Set Game channel volume to 0.8")
    else:
        print("✗ Failed to set channel volume")
    
    # Test setting channel mute
    success = await engine.set_channel_mute(ChannelType.CHAT, True)
    if success:
        print("✓ Muted Chat channel")
    else:
        print("✗ Failed to mute channel")


async def test_master_volume(engine: AudioEngine):
    """Test master volume control"""
    print("\nTesting master volume control...")
    
    # Get current master volume
    current_volume = await engine.get_settings()
    print(f"  Current master volume: {current_volume.master_volume:.2f}")
    
    # Set master volume
    success = await engine.set_master_volume(0.7)
    if success:
        print("✓ Set master volume to 0.7")
    else:
        print("✗ Failed to set master volume")
    
    # Mute master
    success = await engine.set_master_mute(True)
    if success:
        print("✓ Muted master")
    else:
        print("✗ Failed to mute master")


async def test_presets(engine: AudioEngine):
    """Test preset management"""
    print("\nTesting preset management...")
    
    # Get default presets
    presets = await engine.get_presets()
    print(f"  Found {len(presets)} presets")
    
    for preset in presets:
        print(f"    - {preset.name} ({preset.preset_type.name})")
    
    # Apply a preset
    if presets:
        success = await engine.apply_preset(presets[0].id)
        if success:
            print(f"✓ Applied preset '{presets[0].name}'")
        else:
            print(f"✗ Failed to apply preset '{presets[0].name}'")


async def test_sources(engine: AudioEngine):
    """Test source management"""
    print("\nTesting source management...")
    
    sources = await engine.get_sources()
    print(f"  Found {len(sources)} sources")
    
    for source in sources[:5]:  # Show first 5 sources
        channel = await engine.get_source_channel(source.id)
        channel_name = channel.name if channel else "None"
        print(f"    - {source.name}: {source.source_type.name} -> {channel_name}")
    
    if len(sources) > 5:
        print(f"    ... and {len(sources) - 5} more")


async def test_devices(engine: AudioEngine):
    """Test device management"""
    print("\nTesting device management...")
    
    devices = await engine.get_devices()
    print(f"  Found {len(devices)} devices")
    
    for device in devices[:5]:  # Show first 5 devices
        device_type = "Input" if device.is_input else "Output"
        print(f"    - {device.name}: {device_type} ({device.api})")
    
    if len(devices) > 5:
        print(f"    ... and {len(devices) - 5} more")


async def test_state(engine: AudioEngine):
    """Test getting full state"""
    print("\nTesting full state retrieval...")
    
    state = await engine.get_full_state()
    
    print(f"  Engine state: {state['engine']['state']}")
    print(f"  Channels: {len(state['channels'])}")
    print(f"  Sources: {len(state['sources'])}")
    print(f"  Devices: {len(state['devices'])}")
    print(f"  Presets: {len(state['presets'])}")
    
    print("✓ Full state retrieved successfully")


async def test_spatial_audio(engine: AudioEngine):
    """Test spatial audio"""
    print("\nTesting spatial audio...")
    
    # Get spatial settings
    settings = await engine.get_spatial_settings()
    print(f"  Spatial audio enabled: {settings.get('enabled', False)}")
    print(f"  Mode: {settings.get('mode', 'N/A')}")
    
    # Enable spatial for a channel
    success = await engine.enable_spatial_for_channel(
        ChannelType.GAME,
        position=(1.0, 0.0, 0.0)
    )
    if success:
        print("✓ Enabled spatial audio for Game channel")
    else:
        print("✗ Failed to enable spatial audio")


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Linux Sound Manager - Test Suite")
    print("=" * 60)
    
    engine = None
    
    try:
        # Test initialization
        engine = await test_initialization()
        if not engine:
            print("\n✗ Engine initialization failed, skipping other tests")
            return
        
        # Run all tests
        await test_channels(engine)
        await test_master_volume(engine)
        await test_presets(engine)
        await test_sources(engine)
        await test_devices(engine)
        await test_state(engine)
        await test_spatial_audio(engine)
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if engine:
            await engine.shutdown()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
