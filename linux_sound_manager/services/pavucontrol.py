"""
Pavucontrol Integration

This module provides integration with pavucontrol, a PulseAudio/PipeWire
volume control application.

Pavucontrol provides:
- Volume control for applications and devices
- Device switching
- Input/output routing
- Basic audio device management

We'll use D-Bus or command-line interface to interact with pavucontrol.
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Callable, Awaitable
import logging

from ..models.audio_device import AudioDevice, DeviceType, DeviceState
from ..models.audio_source import AudioSource, SourceType, SourceState
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PavucontrolConnectionMethod(Enum):
    """Methods to connect to pavucontrol"""
    DBUS = auto()       # D-Bus interface
    CLI = auto()        # Command-line interface (pactl)


@dataclass
class PavucontrolDevice:
    """Represents a device in pavucontrol"""
    id: str
    name: str
    description: str
    device_type: DeviceType
    volume: float
    muted: bool
    is_default: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "device_type": self.device_type.name,
            "volume": self.volume,
            "muted": self.muted,
            "is_default": self.is_default,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PavucontrolDevice":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            device_type=DeviceType[data.get("device_type", "VIRTUAL")],
            volume=data.get("volume", 1.0),
            muted=data.get("muted", False),
            is_default=data.get("is_default", False),
        )


@dataclass
class PavucontrolApplication:
    """Represents an application in pavucontrol"""
    id: str
    name: str
    process_id: int
    sink_id: str
    source_id: str
    volume: float
    muted: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "process_id": self.process_id,
            "sink_id": self.sink_id,
            "source_id": self.source_id,
            "volume": self.volume,
            "muted": self.muted,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PavucontrolApplication":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            process_id=data.get("process_id", 0),
            sink_id=data.get("sink_id", ""),
            source_id=data.get("source_id", ""),
            volume=data.get("volume", 1.0),
            muted=data.get("muted", False),
        )


class PavucontrolIntegration:
    """
    Provides integration with pavucontrol for audio device and application management.
    
    This class allows the Linux Sound Manager to:
    - List and control audio devices
    - List and control applications
    - Switch default devices
    - Control volumes and mute states
    """
    
    def __init__(self):
        self._connection_method = PavucontrolConnectionMethod.CLI
        self._devices: Dict[str, PavucontrolDevice] = {}
        self._applications: Dict[str, PavucontrolApplication] = {}
        self._event_listeners: List[Callable[[str, Any], Awaitable[None]]] = []
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize pavucontrol integration"""
        try:
            # Check if pavucontrol/pactl is available
            if not await self._check_pactl_available():
                logger.warning("pactl is not available")
                return False
            
            # Try to connect via D-Bus first
            if await self._try_dbus_connection():
                self._connection_method = PavucontrolConnectionMethod.DBUS
                logger.info("Connected to pavucontrol via D-Bus")
            else:
                self._connection_method = PavucontrolConnectionMethod.CLI
                logger.info("Using pavucontrol CLI interface (pactl)")
            
            # Load devices and applications
            await self._load_devices()
            await self._load_applications()
            
            self._initialized = True
            logger.info("Pavucontrol integration initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize pavucontrol integration: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown pavucontrol integration"""
        self._initialized = False
        logger.info("Pavucontrol integration shutdown")
    
    async def _check_pactl_available(self) -> bool:
        """Check if pactl is available"""
        try:
            result = await asyncio.create_subprocess_exec(
                "which", "pactl",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    async def _try_dbus_connection(self) -> bool:
        """Try to connect to pavucontrol via D-Bus"""
        try:
            # Check if PulseAudio/PipeWire D-Bus service is available
            result = await asyncio.create_subprocess_exec(
                "dbus-send",
                "--print-reply",
                "--dest=org.PulseAudio1",
                "/",
                "org.freedesktop.DBus.Properties.Get",
                "string:org.PulseAudio.Server",
                "string:Version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"D-Bus connection failed: {e}")
            return False
    
    async def _load_devices(self) -> None:
        """Load all audio devices"""
        try:
            if self._connection_method == PavucontrolConnectionMethod.DBUS:
                await self._load_devices_dbus()
            else:
                await self._load_devices_cli()
        except Exception as e:
            logger.error(f"Failed to load devices: {e}")
    
    async def _load_devices_dbus(self) -> None:
        """Load devices via D-Bus"""
        # Implementation would use D-Bus
        logger.info("Loading devices via D-Bus")
    
    async def _load_devices_cli(self) -> None:
        """Load devices via pactl CLI"""
        try:
            # List sinks (output devices)
            result = await asyncio.create_subprocess_exec(
                "pactl", "list", "sinks", "short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                self._parse_sinks(stdout.decode())
            
            # List sources (input devices)
            result = await asyncio.create_subprocess_exec(
                "pactl", "list", "sources", "short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                self._parse_sources(stdout.decode())
            
            logger.info(f"Loaded {len(self._devices)} devices via CLI")
            
        except Exception as e:
            logger.error(f"Failed to load devices via CLI: {e}")
    
    def _parse_sinks(self, output: str) -> None:
        """Parse sink (output device) information"""
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) >= 4:
                device_id = parts[0].strip()
                name = parts[1].strip()
                description = parts[2].strip() if len(parts) > 2 else ""
                
                device = PavucontrolDevice(
                    id=device_id,
                    name=name,
                    description=description,
                    device_type=DeviceType.OUTPUT,
                    volume=1.0,
                    muted=False,
                    is_default="default" in line.lower(),
                )
                self._devices[device_id] = device
    
    def _parse_sources(self, output: str) -> None:
        """Parse source (input device) information"""
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) >= 4:
                device_id = parts[0].strip()
                name = parts[1].strip()
                description = parts[2].strip() if len(parts) > 2 else ""
                
                device = PavucontrolDevice(
                    id=device_id,
                    name=name,
                    description=description,
                    device_type=DeviceType.INPUT,
                    volume=1.0,
                    muted=False,
                    is_default="default" in line.lower(),
                )
                self._devices[device_id] = device
    
    async def _load_applications(self) -> None:
        """Load all applications"""
        try:
            if self._connection_method == PavucontrolConnectionMethod.DBUS:
                await self._load_applications_dbus()
            else:
                await self._load_applications_cli()
        except Exception as e:
            logger.error(f"Failed to load applications: {e}")
    
    async def _load_applications_dbus(self) -> None:
        """Load applications via D-Bus"""
        # Implementation would use D-Bus
        logger.info("Loading applications via D-Bus")
    
    async def _load_applications_cli(self) -> None:
        """Load applications via pactl CLI"""
        try:
            # List sink inputs (application outputs)
            result = await asyncio.create_subprocess_exec(
                "pactl", "list", "sink-inputs", "short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                self._parse_sink_inputs(stdout.decode())
            
            # List source outputs (application inputs)
            result = await asyncio.create_subprocess_exec(
                "pactl", "list", "source-outputs", "short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                self._parse_source_outputs(stdout.decode())
            
            logger.info(f"Loaded {len(self._applications)} applications via CLI")
            
        except Exception as e:
            logger.error(f"Failed to load applications via CLI: {e}")
    
    def _parse_sink_inputs(self, output: str) -> None:
        """Parse sink input (application output) information"""
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) >= 3:
                app_id = parts[0].strip()
                sink_id = parts[1].strip()
                name = parts[2].strip()
                
                # Extract process ID if available
                process_id = 0
                if '#' in app_id:
                    try:
                        process_id = int(app_id.split('#')[1])
                    except ValueError:
                        pass
                
                app = PavucontrolApplication(
                    id=app_id,
                    name=name,
                    process_id=process_id,
                    sink_id=sink_id,
                    source_id="",
                    volume=1.0,
                    muted=False,
                )
                self._applications[app_id] = app
    
    def _parse_source_outputs(self, output: str) -> None:
        """Parse source output (application input) information"""
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) >= 3:
                app_id = parts[0].strip()
                source_id = parts[1].strip()
                name = parts[2].strip()
                
                # Extract process ID if available
                process_id = 0
                if '#' in app_id:
                    try:
                        process_id = int(app_id.split('#')[1])
                    except ValueError:
                        pass
                
                # Update existing application or create new
                if app_id in self._applications:
                    self._applications[app_id].source_id = source_id
                else:
                    app = PavucontrolApplication(
                        id=app_id,
                        name=name,
                        process_id=process_id,
                        sink_id="",
                        source_id=source_id,
                        volume=1.0,
                        muted=False,
                    )
                    self._applications[app_id] = app
    
    async def get_devices(self) -> List[PavucontrolDevice]:
        """Get all audio devices"""
        return list(self._devices.values())
    
    async def get_applications(self) -> List[PavucontrolApplication]:
        """Get all applications"""
        return list(self._applications.values())
    
    async def get_output_devices(self) -> List[PavucontrolDevice]:
        """Get all output devices"""
        return [d for d in self._devices.values() if d.device_type == DeviceType.OUTPUT]
    
    async def get_input_devices(self) -> List[PavucontrolDevice]:
        """Get all input devices"""
        return [d for d in self._devices.values() if d.device_type == DeviceType.INPUT]
    
    async def set_device_volume(self, device_id: str, volume: float) -> bool:
        """Set volume for a device"""
        try:
            if self._connection_method == PavucontrolConnectionMethod.DBUS:
                return await self._set_device_volume_dbus(device_id, volume)
            else:
                return await self._set_device_volume_cli(device_id, volume)
            
        except Exception as e:
            logger.error(f"Failed to set device volume: {e}")
            return False
    
    async def _set_device_volume_dbus(self, device_id: str, volume: float) -> bool:
        """Set device volume via D-Bus"""
        try:
            # Implementation would use D-Bus
            return True
        except Exception as e:
            logger.error(f"Failed to set device volume via D-Bus: {e}")
            return False
    
    async def _set_device_volume_cli(self, device_id: str, volume: float) -> bool:
        """Set device volume via CLI"""
        try:
            # Convert volume to percentage (0-100)
            volume_percent = int(volume * 100)
            
            # Use pactl to set volume
            result = await asyncio.create_subprocess_exec(
                "pactl", "set-sink-volume", device_id, f"{volume_percent}%",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to set device volume: {stderr.decode()}")
                return False
            
            # Update local state
            if device_id in self._devices:
                self._devices[device_id].volume = volume
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set device volume via CLI: {e}")
            return False
    
    async def set_device_mute(self, device_id: str, muted: bool) -> bool:
        """Set mute state for a device"""
        try:
            if self._connection_method == PavucontrolConnectionMethod.DBUS:
                return await self._set_device_mute_dbus(device_id, muted)
            else:
                return await self._set_device_mute_cli(device_id, muted)
            
        except Exception as e:
            logger.error(f"Failed to set device mute: {e}")
            return False
    
    async def _set_device_mute_dbus(self, device_id: str, muted: bool) -> bool:
        """Set device mute via D-Bus"""
        try:
            return True
        except Exception as e:
            logger.error(f"Failed to set device mute via D-Bus: {e}")
            return False
    
    async def _set_device_mute_cli(self, device_id: str, muted: bool) -> bool:
        """Set device mute via CLI"""
        try:
            action = "mute" if muted else "unmute"
            
            result = await asyncio.create_subprocess_exec(
                "pactl", "set-sink-mute", device_id, action,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to set device mute: {stderr.decode()}")
                return False
            
            # Update local state
            if device_id in self._devices:
                self._devices[device_id].muted = muted
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set device mute via CLI: {e}")
            return False
    
    async def set_application_volume(self, app_id: str, volume: float) -> bool:
        """Set volume for an application"""
        try:
            if self._connection_method == PavucontrolConnectionMethod.DBUS:
                return await self._set_application_volume_dbus(app_id, volume)
            else:
                return await self._set_application_volume_cli(app_id, volume)
            
        except Exception as e:
            logger.error(f"Failed to set application volume: {e}")
            return False
    
    async def _set_application_volume_dbus(self, app_id: str, volume: float) -> bool:
        """Set application volume via D-Bus"""
        try:
            return True
        except Exception as e:
            logger.error(f"Failed to set application volume via D-Bus: {e}")
            return False
    
    async def _set_application_volume_cli(self, app_id: str, volume: float) -> bool:
        """Set application volume via CLI"""
        try:
            # Convert volume to percentage (0-100)
            volume_percent = int(volume * 100)
            
            # Use pactl to set volume
            result = await asyncio.create_subprocess_exec(
                "pactl", "set-sink-input-volume", app_id, f"{volume_percent}%",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to set application volume: {stderr.decode()}")
                return False
            
            # Update local state
            if app_id in self._applications:
                self._applications[app_id].volume = volume
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set application volume via CLI: {e}")
            return False
    
    async def set_application_mute(self, app_id: str, muted: bool) -> bool:
        """Set mute state for an application"""
        try:
            if self._connection_method == PavucontrolConnectionMethod.DBUS:
                return await self._set_application_mute_dbus(app_id, muted)
            else:
                return await self._set_application_mute_cli(app_id, muted)
            
        except Exception as e:
            logger.error(f"Failed to set application mute: {e}")
            return False
    
    async def _set_application_mute_dbus(self, app_id: str, muted: bool) -> bool:
        """Set application mute via D-Bus"""
        try:
            return True
        except Exception as e:
            logger.error(f"Failed to set application mute via D-Bus: {e}")
            return False
    
    async def _set_application_mute_cli(self, app_id: str, muted: bool) -> bool:
        """Set application mute via CLI"""
        try:
            action = "mute" if muted else "unmute"
            
            result = await asyncio.create_subprocess_exec(
                "pactl", "set-sink-input-mute", app_id, action,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to set application mute: {stderr.decode()}")
                return False
            
            # Update local state
            if app_id in self._applications:
                self._applications[app_id].muted = muted
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set application mute via CLI: {e}")
            return False
    
    async def move_application_to_device(
        self, 
        app_id: str, 
        device_id: str
    ) -> bool:
        """Move an application to a different device"""
        try:
            if self._connection_method == PavucontrolConnectionMethod.DBUS:
                return await self._move_application_to_device_dbus(app_id, device_id)
            else:
                return await self._move_application_to_device_cli(app_id, device_id)
            
        except Exception as e:
            logger.error(f"Failed to move application to device: {e}")
            return False
    
    async def _move_application_to_device_dbus(
        self, 
        app_id: str, 
        device_id: str
    ) -> bool:
        """Move application to device via D-Bus"""
        try:
            return True
        except Exception as e:
            logger.error(f"Failed to move application to device via D-Bus: {e}")
            return False
    
    async def _move_application_to_device_cli(
        self, 
        app_id: str, 
        device_id: str
    ) -> bool:
        """Move application to device via CLI"""
        try:
            # Use pactl to move sink input
            result = await asyncio.create_subprocess_exec(
                "pactl", "move-sink-input", app_id, device_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to move application: {stderr.decode()}")
                return False
            
            # Update local state
            if app_id in self._applications:
                self._applications[app_id].sink_id = device_id
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move application to device via CLI: {e}")
            return False
    
    async def set_default_output_device(self, device_id: str) -> bool:
        """Set the default output device"""
        try:
            if self._connection_method == PavucontrolConnectionMethod.DBUS:
                return await self._set_default_output_device_dbus(device_id)
            else:
                return await self._set_default_output_device_cli(device_id)
            
        except Exception as e:
            logger.error(f"Failed to set default output device: {e}")
            return False
    
    async def _set_default_output_device_dbus(self, device_id: str) -> bool:
        """Set default output device via D-Bus"""
        try:
            return True
        except Exception as e:
            logger.error(f"Failed to set default output device via D-Bus: {e}")
            return False
    
    async def _set_default_output_device_cli(self, device_id: str) -> bool:
        """Set default output device via CLI"""
        try:
            # Use pactl to set default sink
            result = await asyncio.create_subprocess_exec(
                "pactl", "set-default-sink", device_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to set default output device: {stderr.decode()}")
                return False
            
            # Update local state
            for d in self._devices.values():
                d.is_default = (d.id == device_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set default output device via CLI: {e}")
            return False
    
    async def set_default_input_device(self, device_id: str) -> bool:
        """Set the default input device"""
        try:
            if self._connection_method == PavucontrolConnectionMethod.DBUS:
                return await self._set_default_input_device_dbus(device_id)
            else:
                return await self._set_default_input_device_cli(device_id)
            
        except Exception as e:
            logger.error(f"Failed to set default input device: {e}")
            return False
    
    async def _set_default_input_device_dbus(self, device_id: str) -> bool:
        """Set default input device via D-Bus"""
        try:
            return True
        except Exception as e:
            logger.error(f"Failed to set default input device via D-Bus: {e}")
            return False
    
    async def _set_default_input_device_cli(self, device_id: str) -> bool:
        """Set default input device via CLI"""
        try:
            # Use pactl to set default source
            result = await asyncio.create_subprocess_exec(
                "pactl", "set-default-source", device_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to set default input device: {stderr.decode()}")
                return False
            
            # Update local state
            for d in self._devices.values():
                d.is_default = (d.id == device_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set default input device via CLI: {e}")
            return False
    
    async def refresh(self) -> None:
        """Refresh the list of devices and applications"""
        await self._load_devices()
        await self._load_applications()
    
    def add_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Add an event listener for pavucontrol events"""
        self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Remove an event listener"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of pavucontrol integration"""
        return {
            "initialized": self._initialized,
            "connection_method": self._connection_method.name,
            "devices_count": len(self._devices),
            "applications_count": len(self._applications),
        }
