"""
Main entry point for Linux Sound Manager

This module provides the main application entry point and CLI interface.
"""

import asyncio
import argparse
import signal
import sys
from typing import Optional, List, Dict, Any

# Import logger first to avoid circular imports
from .utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

# Global instances - will be imported lazily
_engine = None
_config_manager = None


async def get_engine():
    """Lazy import of AudioEngine to avoid circular imports"""
    global _engine
    if _engine is None:
        from .core.audio_engine import AudioEngine
        _engine = AudioEngine()
    return _engine


async def get_config_manager():
    """Lazy import of ConfigManager to avoid circular imports"""
    global _config_manager
    if _config_manager is None:
        from .utils.config_manager import ConfigManager
        _config_manager = ConfigManager()
    return _config_manager


async def initialize_application() -> bool:
    """Initialize the application"""
    global _engine, _config_manager
    
    try:
        # Set up logging
        setup_logging()
        
        # Initialize configuration manager
        _config_manager = await get_config_manager()
        if not await _config_manager.initialize():
            logger.error("Failed to initialize configuration manager")
            return False
        
        # Initialize audio engine
        _engine = await get_engine()
        if not await _engine.initialize():
            logger.error("Failed to initialize audio engine")
            return False
        
        # Start audio processing
        if not await _engine.start_audio_processing():
            logger.error("Failed to start audio processing")
            return False
        
        logger.info("Linux Sound Manager initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        import traceback
        traceback.print_exc()
        return False


async def shutdown_application() -> None:
    """Shutdown the application"""
    global _engine, _config_manager
    
    try:
        if _engine:
            await _engine.shutdown()
        
        if _config_manager:
            await _config_manager.shutdown()
        
        logger.info("Linux Sound Manager shutdown successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def handle_signal(signame: str) -> None:
    """Handle system signals"""
    logger.info(f"Received signal: {signame}")
    
    async def shutdown():
        await shutdown_application()
        sys.exit(0)
    
    asyncio.create_task(shutdown())


async def list_devices() -> None:
    """List all audio devices"""
    engine = await get_engine()
    if not engine:
        print("Error: Engine not initialized")
        return
    
    devices = await engine.get_devices()
    
    print("\nAudio Devices:")
    print("-" * 60)
    
    for device in devices:
        device_type = "Input" if device.is_input else "Output"
        default_marker = " (Default)" if device.state.name == "CONNECTED" else ""
        print(f"{device.name:30} {device_type:8} {device.description}{default_marker}")
    
    print(f"\nTotal: {len(devices)} devices")


async def list_sources() -> None:
    """List all audio sources"""
    engine = await get_engine()
    if not engine:
        print("Error: Engine not initialized")
        return
    
    sources = await engine.get_sources()
    
    print("\nAudio Sources:")
    print("-" * 60)
    
    for source in sources:
        source_type = source.source_type.name
        channel = await engine.get_source_channel(source.id)
        channel_name = channel.name if channel else "None"
        
        print(f"{source.name:30} {source_type:12} {source.state.name:10} -> {channel_name}")
    
    print(f"\nTotal: {len(sources)} sources")


async def list_channels() -> None:
    """List all channels"""
    engine = await get_engine()
    if not engine:
        print("Error: Engine not initialized")
        return
    
    channels = await engine.get_channels()
    
    print("\nAudio Channels:")
    print("-" * 60)
    
    for channel in channels:
        muted = "Muted" if channel.settings.muted else "Active"
        sources = await engine.get_sources_in_channel(channel.channel_type)
        
        print(f"{channel.name:12} Volume: {channel.settings.volume:.2f} {muted:8} Sources: {len(sources)}")
    
    print(f"\nTotal: {len(channels)} channels")


async def list_presets() -> None:
    """List all presets"""
    engine = await get_engine()
    if not engine:
        print("Error: Engine not initialized")
        return
    
    presets = await engine.get_presets()
    current_preset = await engine.get_current_preset()
    
    print("\nPresets:")
    print("-" * 60)
    
    for preset in presets:
        current_marker = " *" if current_preset and current_preset.id == preset.id else ""
        factory_marker = " (Factory)" if preset.is_factory else ""
        
        print(f"{preset.name:30} {preset.preset_type.name:12}{current_marker}{factory_marker}")
    
    print(f"\nTotal: {len(presets)} presets")


async def show_status() -> None:
    """Show application status"""
    engine = await get_engine()
    if not engine:
        print("Error: Engine not initialized")
        return
    
    state = await engine.get_full_state()
    
    print("\nApplication Status:")
    print("-" * 60)
    print(f"Engine State: {state['engine']['state']}")
    print(f"Sample Rate: {state['engine']['settings']['sample_rate']} Hz")
    print(f"Buffer Size: {state['engine']['settings']['buffer_size']}")
    print(f"Spatial Audio: {'Enabled' if state['engine']['settings']['enable_spatial'] else 'Disabled'}")
    print(f"Effects: {'Enabled' if state['engine']['settings']['enable_effects'] else 'Disabled'}")
    
    print(f"\nChannels:")
    for channel_name, channel_data in state['channels'].items():
        print(f"  {channel_name:12} Volume: {channel_data['volume']:.2f} Muted: {channel_data['muted']}")
    
    print(f"\nDevices: {len(state['devices'])} total")
    print(f"Sources: {len(state['sources'])} total")
    print(f"Presets: {len(state['presets'])} total")


async def set_channel_volume(args: argparse.Namespace) -> None:
    """Set channel volume"""
    engine = await get_engine()
    if not engine:
        print("Error: Engine not initialized")
        return
    
    try:
        channel_type = getattr(args, 'channel', 'game').upper()
        volume = float(getattr(args, 'volume', 1.0))
        
        # Map channel name to ChannelType
        from .core.channels import ChannelType
        channel_type_map = {
            'GAME': ChannelType.GAME,
            'CHAT': ChannelType.CHAT,
            'MEDIA': ChannelType.MEDIA,
            'AUX': ChannelType.AUX,
            'MICROPHONE': ChannelType.MICROPHONE,
            'MASTER': ChannelType.MASTER,
        }
        
        if channel_type not in channel_type_map:
            print(f"Error: Unknown channel '{channel_type}'")
            return
        
        success = await engine.set_channel_volume(channel_type_map[channel_type], volume)
        if success:
            print(f"Set {channel_type} volume to {volume:.2f}")
        else:
            print(f"Error: Failed to set {channel_type} volume")
            
    except ValueError:
        print("Error: Invalid volume value")


async def set_channel_mute(args: argparse.Namespace) -> None:
    """Set channel mute state"""
    engine = await get_engine()
    if not engine:
        print("Error: Engine not initialized")
        return
    
    try:
        channel_type = getattr(args, 'channel', 'game').upper()
        muted = getattr(args, 'mute', True)
        
        # Map channel name to ChannelType
        from .core.channels import ChannelType
        channel_type_map = {
            'GAME': ChannelType.GAME,
            'CHAT': ChannelType.CHAT,
            'MEDIA': ChannelType.MEDIA,
            'AUX': ChannelType.AUX,
            'MICROPHONE': ChannelType.MICROPHONE,
            'MASTER': ChannelType.MASTER,
        }
        
        if channel_type not in channel_type_map:
            print(f"Error: Unknown channel '{channel_type}'")
            return
        
        success = await engine.set_channel_mute(channel_type_map[channel_type], muted)
        if success:
            state = "muted" if muted else "unmuted"
            print(f"Set {channel_type} to {state}")
        else:
            print(f"Error: Failed to set {channel_type} mute state")
            
    except ValueError:
        print("Error: Invalid mute value")


async def set_master_volume(args: argparse.Namespace) -> None:
    """Set master volume"""
    engine = await get_engine()
    if not engine:
        print("Error: Engine not initialized")
        return
    
    try:
        volume = float(getattr(args, 'volume', 1.0))
        success = await engine.set_master_volume(volume)
        if success:
            print(f"Set master volume to {volume:.2f}")
        else:
            print("Error: Failed to set master volume")
    except ValueError:
        print("Error: Invalid volume value")


async def assign_source(args: argparse.Namespace) -> None:
    """Assign a source to a channel"""
    engine = await get_engine()
    if not engine:
        print("Error: Engine not initialized")
        return
    
    try:
        source_id = getattr(args, 'source', '')
        channel_type = getattr(args, 'channel', 'game').upper()
        
        # Map channel name to ChannelType
        from .core.channels import ChannelType
        channel_type_map = {
            'GAME': ChannelType.GAME,
            'CHAT': ChannelType.CHAT,
            'MEDIA': ChannelType.MEDIA,
            'AUX': ChannelType.AUX,
            'MICROPHONE': ChannelType.MICROPHONE,
        }
        
        if channel_type not in channel_type_map:
            print(f"Error: Unknown channel '{channel_type}'")
            return
        
        # Find source by name or ID
        sources = await engine.get_sources()
        target_source = None
        
        for source in sources:
            if source.id == source_id or source.name == source_id:
                target_source = source
                break
        
        if not target_source:
            print(f"Error: Source '{source_id}' not found")
            return
        
        success = await engine.assign_source_to_channel(
            target_source.id, 
            channel_type_map[channel_type]
        )
        
        if success:
            print(f"Assigned '{target_source.name}' to {channel_type}")
        else:
            print(f"Error: Failed to assign source to channel")
            
    except Exception as e:
        print(f"Error: {e}")


async def apply_preset(args: argparse.Namespace) -> None:
    """Apply a preset"""
    engine = await get_engine()
    if not engine:
        print("Error: Engine not initialized")
        return
    
    try:
        preset_name = getattr(args, 'preset', '')
        
        # Find preset by name or ID
        presets = await engine.get_presets()
        target_preset = None
        
        for preset in presets:
            if preset.id == preset_name or preset.name == preset_name:
                target_preset = preset
                break
        
        if not target_preset:
            print(f"Error: Preset '{preset_name}' not found")
            return
        
        success = await engine.apply_preset(target_preset.id)
        if success:
            print(f"Applied preset '{target_preset.name}'")
        else:
            print(f"Error: Failed to apply preset")
            
    except Exception as e:
        print(f"Error: {e}")


async def run_cli() -> None:
    """Run the command-line interface"""
    parser = argparse.ArgumentParser(
        description="Linux Sound Manager - Audio Mixer for Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lsm status                    Show application status
  lsm devices                   List audio devices
  lsm sources                   List audio sources
  lsm channels                  List channels
  lsm presets                   List presets
  lsm set-volume game 0.8      Set Game channel volume to 0.8
  lsm set-mute chat true        Mute Chat channel
  lsm set-master-volume 0.5    Set master volume to 0.5
  lsm assign firefox game       Assign Firefox to Game channel
  lsm apply gaming              Apply Gaming preset
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show application status')
    
    # Devices command
    subparsers.add_parser('devices', help='List audio devices')
    
    # Sources command
    subparsers.add_parser('sources', help='List audio sources')
    
    # Channels command
    subparsers.add_parser('channels', help='List channels')
    
    # Presets command
    subparsers.add_parser('presets', help='List presets')
    
    # Set volume command
    volume_parser = subparsers.add_parser('set-volume', help='Set channel volume')
    volume_parser.add_argument('channel', help='Channel name (game, chat, media, aux, microphone, master)')
    volume_parser.add_argument('volume', type=float, help='Volume (0.0 to 1.0)')
    
    # Set mute command
    mute_parser = subparsers.add_parser('set-mute', help='Set channel mute state')
    mute_parser.add_argument('channel', help='Channel name (game, chat, media, aux, microphone, master)')
    mute_parser.add_argument('mute', type=bool, help='Mute state (true/false)')
    
    # Set master volume command
    master_volume_parser = subparsers.add_parser('set-master-volume', help='Set master volume')
    master_volume_parser.add_argument('volume', type=float, help='Volume (0.0 to 1.0)')
    
    # Assign source command
    assign_parser = subparsers.add_parser('assign', help='Assign source to channel')
    assign_parser.add_argument('source', help='Source name or ID')
    assign_parser.add_argument('channel', help='Channel name (game, chat, media, aux, microphone)')
    
    # Apply preset command
    apply_parser = subparsers.add_parser('apply', help='Apply a preset')
    apply_parser.add_argument('preset', help='Preset name or ID')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not hasattr(args, 'command'):
        parser.print_help()
        return
    
    # Initialize application
    if not await initialize_application():
        print("Failed to initialize application")
        return
    
    try:
        # Handle commands
        if args.command == 'status':
            await show_status()
        elif args.command == 'devices':
            await list_devices()
        elif args.command == 'sources':
            await list_sources()
        elif args.command == 'channels':
            await list_channels()
        elif args.command == 'presets':
            await list_presets()
        elif args.command == 'set-volume':
            await set_channel_volume(args)
        elif args.command == 'set-mute':
            await set_channel_mute(args)
        elif args.command == 'set-master-volume':
            await set_master_volume(args)
        elif args.command == 'assign':
            await assign_source(args)
        elif args.command == 'apply':
            await apply_preset(args)
        else:
            print(f"Unknown command: {args.command}")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await shutdown_application()


async def run_service() -> None:
    """Run as a background service"""
    # Initialize application
    if not await initialize_application():
        print("Failed to initialize application")
        return
    
    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Error in service mode: {e}")
    finally:
        await shutdown_application()


def main() -> None:
    """Main entry point"""
    # Set up signal handlers
    loop = asyncio.new_event_loop()
    
    for signame in ('SIGINT', 'SIGTERM'):
        signal.signal(
            getattr(signal, signame),
            lambda signum, frame: handle_signal(signame)
        )
    
    # Check if we should run as a service
    import sys
    if '--service' in sys.argv:
        loop.run_until_complete(run_service())
    else:
        loop.run_until_complete(run_cli())


if __name__ == '__main__':
    main()
