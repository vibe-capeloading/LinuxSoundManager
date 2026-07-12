"""
PipeWire Manager - Low-level PipeWire integration

This module provides direct integration with PipeWire for audio device management,
virtual device creation, and audio routing.
"""

import asyncio
import json
import subprocess
import re
from typing import Optional, List, Dict, Any, Tuple, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum, auto
import logging

from ..models.audio_device import AudioDevice, DeviceType, DeviceState
from ..models.audio_source import AudioSource, SourceType, SourceState
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PipeWireNodeType(Enum):
    """PipeWire node types"""
    SINK = auto()      # Audio output
    SOURCE = auto()    # Audio input
    SINK_INPUT = auto() # Input to a sink (application output)
    SOURCE_OUTPUT = auto() # Output from a source (application input)
    MONITOR = auto()   # Monitor of a sink


@dataclass
class PipeWireNode:
    """Represents a PipeWire node"""
    id: int
    name: str
    node_type: PipeWireNodeType
    description: str = ""
    application_id: Optional[str] = None
    process_id: Optional[int] = None
    volume: float = 1.0
    muted: bool = False
    state: str = "idle"
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipeWireLink:
    """Represents a connection between PipeWire nodes"""
    id: int
    input_node_id: int
    output_node_id: int
    input_port_id: int
    output_port_id: int
    state: str = "active"


class PipeWireManager:
    """
    Manages PipeWire audio system interactions.
    
    Provides functionality for:
    - Enumerating audio devices
    - Creating virtual audio devices
    - Managing audio routing
    - Controlling volume and mute
    - Monitoring audio levels
    """
    
    def __init__(self):
        self._nodes: Dict[int, PipeWireNode] = {}
        self._links: Dict[int, PipeWireLink] = {}
        self._sources: Dict[str, AudioSource] = {}
        self._devices: Dict[str, AudioDevice] = {}
        self._event_listeners: List[Callable[[str, Any], Awaitable[None]]] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> bool:
        """Initialize PipeWire manager"""
        try:
            # Check if PipeWire is running
            if not await self._check_pipewire_running():
                logger.error("PipeWire is not running")
                return False
            
            # Load initial state
            await self._load_nodes()
            await self._load_devices()
            
            self._running = True
            logger.info("PipeWire manager initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PipeWire manager: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown PipeWire manager"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("PipeWire manager shutdown")
    
    async def _check_pipewire_running(self) -> bool:
        """Check if PipeWire is running"""
        try:
            result = await asyncio.create_subprocess_exec(
                "pipewire", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    async def _load_nodes(self) -> None:
        """Load all PipeWire nodes"""
        try:
            # Use pw-cli to list nodes
            result = await asyncio.create_subprocess_exec(
                "pw-cli", "list-objects", "Node",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode != 0:
                logger.warning("Failed to list PipeWire nodes")
                return
            
            # Parse node information
            nodes = self._parse_pw_cli_output(stdout.decode())
            self._nodes = {n.id: n for n in nodes}
            
            # Update sources from nodes
            await self._update_sources_from_nodes()
            
        except Exception as e:
            logger.error(f"Failed to load nodes: {e}")
    
    async def _load_devices(self) -> None:
        """Load all audio devices"""
        try:
            # Use pw-cli to list devices
            result = await asyncio.create_subprocess_exec(
                "pw-cli", "list-objects", "Device",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode != 0:
                logger.warning("Failed to list PipeWire devices")
                return
            
            # Parse device information
            devices = self._parse_devices(stdout.decode())
            self._devices = {d.id: d for d in devices}
            
        except Exception as e:
            logger.error(f"Failed to load devices: {e}")
    
    def _parse_pw_cli_output(self, output: str) -> List[PipeWireNode]:
        """Parse pw-cli output to extract nodes"""
        nodes = []
        
        # Parse node entries
        node_blocks = re.split(r'id \d+', output)
        
        for block in node_blocks:
            if not block.strip():
                continue
            
            # Extract node info
            node_id_match = re.search(r'id (\d+)', block)
            if not node_id_match:
                continue
            
            node_id = int(node_id_match.group(1))
            
            # Extract type
            type_match = re.search(r'type\s+(\w+)', block)
            node_type_str = type_match.group(1) if type_match else ""
            node_type = self._map_node_type(node_type_str)
            
            # Extract name
            name_match = re.search(r'name\s+"([^"]+)"', block)
            name = name_match.group(1) if name_match else f"Node {node_id}"
            
            # Extract description
            desc_match = re.search(r'description\s+"([^"]+)"', block)
            description = desc_match.group(1) if desc_match else ""
            
            # Extract application info
            app_id_match = re.search(r'application\.id\s+"([^"]+)"', block)
            application_id = app_id_match.group(1) if app_id_match else None
            
            # Extract process ID
            pid_match = re.search(r'application\.process\.id\s+(\d+)', block)
            process_id = int(pid_match.group(1)) if pid_match else None
            
            # Extract volume
            vol_match = re.search(r'props\s+\{\s*[^}]*volume\s+(\d+\.\d+)', block)
            volume = float(vol_match.group(1)) if vol_match else 1.0
            
            # Extract mute
            mute_match = re.search(r'mute\s+(\d+)', block)
            muted = bool(int(mute_match.group(1))) if mute_match else False
            
            nodes.append(PipeWireNode(
                id=node_id,
                name=name,
                node_type=node_type,
                description=description,
                application_id=application_id,
                process_id=process_id,
                volume=volume,
                muted=muted,
            ))
        
        return nodes
    
    def _map_node_type(self, type_str: str) -> PipeWireNodeType:
        """Map string type to PipeWireNodeType"""
        type_mapping = {
            "Sink": PipeWireNodeType.SINK,
            "Source": PipeWireNodeType.SOURCE,
            "Sink/Input": PipeWireNodeType.SINK_INPUT,
            "Source/Output": PipeWireNodeType.SOURCE_OUTPUT,
            "Monitor": PipeWireNodeType.MONITOR,
        }
        return type_mapping.get(type_str, PipeWireNodeType.SINK)
    
    def _parse_devices(self, output: str) -> List[AudioDevice]:
        """Parse device information from pw-cli output"""
        devices = []
        
        # Similar parsing logic for devices
        device_blocks = re.split(r'id \d+', output)
        
        for block in device_blocks:
            if not block.strip():
                continue
            
            device_id_match = re.search(r'id (\d+)', block)
            if not device_id_match:
                continue
            
            device_id = str(device_id_match.group(1))
            
            name_match = re.search(r'name\s+"([^"]+)"', block)
            name = name_match.group(1) if name_match else f"Device {device_id}"
            
            desc_match = re.search(r'description\s+"([^"]+)"', block)
            description = desc_match.group(1) if desc_match else ""
            
            # Determine device type
            if "Input" in block or "Capture" in block:
                device_type = DeviceType.INPUT
            elif "Output" in block or "Playback" in block:
                device_type = DeviceType.OUTPUT
            elif "Monitor" in block:
                device_type = DeviceType.MONITOR
            else:
                device_type = DeviceType.VIRTUAL
            
            devices.append(AudioDevice(
                id=device_id,
                name=name,
                description=description,
                device_type=device_type,
                api="pipewire",
                state=DeviceState.CONNECTED,
            ))
        
        return devices
    
    async def _update_sources_from_nodes(self) -> None:
        """Update audio sources from PipeWire nodes"""
        sources = {}
        
        for node_id, node in self._nodes.items():
            # Skip non-application nodes
            if node.node_type not in (PipeWireNodeType.SINK_INPUT, PipeWireNodeType.SOURCE_OUTPUT):
                continue
            
            # Determine source type
            if node.node_type == PipeWireNodeType.SINK_INPUT:
                source_type = SourceType.APPLICATION
            elif node.node_type == PipeWireNodeType.SOURCE_OUTPUT:
                source_type = SourceType.MICROPHONE
            else:
                continue
            
            source = AudioSource(
                id=str(node_id),
                name=node.name,
                source_type=source_type,
                application_id=node.application_id,
                process_id=node.process_id,
                volume=node.volume,
                muted=node.muted,
                state=SourceState.ACTIVE if node.state == "active" else SourceState.INACTIVE,
                properties={"node_id": node_id, "description": node.description}
            )
            sources[str(node_id)] = source
        
        self._sources = sources
    
    async def get_devices(self) -> List[AudioDevice]:
        """Get all audio devices"""
        return list(self._devices.values())
    
    async def get_sources(self) -> List[AudioSource]:
        """Get all audio sources"""
        return list(self._sources.values())
    
    async def get_sinks(self) -> List[AudioDevice]:
        """Get all output devices (sinks)"""
        return [d for d in self._devices.values() if d.is_output]
    
    async def get_sources_by_type(self, source_type: SourceType) -> List[AudioSource]:
        """Get sources by type"""
        return [s for s in self._sources.values() if s.source_type == source_type]
    
    async def create_virtual_sink(self, name: str, description: str = "") -> Optional[AudioDevice]:
        """
        Create a virtual sink (output device)
        
        Uses pw-loopback or pw-jack to create virtual devices
        """
        try:
            # Use pw-loopback to create a virtual sink
            # This creates a sink that can be used as an output
            cmd = [
                "pw-loopback",
                "--capture", "auto",
                "--playback", name,
                "--capture-props", json.dumps({"node.name": f"{name}-capture"}),
                "--playback-props", json.dumps({"node.name": name, "node.description": description}),
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Failed to create virtual sink: {stderr.decode()}")
                return None
            
            # Reload nodes to get the new sink
            await self._load_nodes()
            await self._load_devices()
            
            # Find the new device
            for device in self._devices.values():
                if device.name == name:
                    return device
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create virtual sink: {e}")
            return None
    
    async def create_virtual_source(self, name: str, description: str = "") -> Optional[AudioDevice]:
        """
        Create a virtual source (input device)
        
        Uses pw-loopback to create virtual sources
        """
        try:
            # Similar to virtual sink but for input
            cmd = [
                "pw-loopback",
                "--playback", "auto",
                "--capture", name,
                "--playback-props", json.dumps({"node.name": f"{name}-playback"}),
                "--capture-props", json.dumps({"node.name": name, "node.description": description}),
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Failed to create virtual source: {stderr.decode()}")
                return None
            
            await self._load_nodes()
            await self._load_devices()
            
            for device in self._devices.values():
                if device.name == name:
                    return device
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create virtual source: {e}")
            return None
    
    async def connect_source_to_sink(
        self, 
        source_id: str, 
        sink_id: str,
        source_port: int = 0,
        sink_port: int = 0
    ) -> bool:
        """
        Connect an audio source to a sink
        
        Args:
            source_id: Source node ID
            sink_id: Sink node ID
            source_port: Source port index
            sink_port: Sink port index
        
        Returns:
            True if connection was successful
        """
        try:
            # Use pw-link to create a connection
            cmd = [
                "pw-link",
                f"{source_id}:{source_port}",
                f"{sink_id}:{sink_port}",
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Failed to connect source to sink: {stderr.decode()}")
                return False
            
            # Reload links
            await self._load_links()
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect source to sink: {e}")
            return False
    
    async def _load_links(self) -> None:
        """Load all PipeWire links"""
        try:
            result = await asyncio.create_subprocess_exec(
                "pw-cli", "list-objects", "Link",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode != 0:
                logger.warning("Failed to list PipeWire links")
                return
            
            # Parse links
            links = self._parse_links(stdout.decode())
            self._links = {l.id: l for l in links}
            
        except Exception as e:
            logger.error(f"Failed to load links: {e}")
    
    def _parse_links(self, output: str) -> List[PipeWireLink]:
        """Parse link information from pw-cli output"""
        links = []
        
        link_blocks = re.split(r'id \d+', output)
        
        for block in link_blocks:
            if not block.strip():
                continue
            
            link_id_match = re.search(r'id (\d+)', block)
            if not link_id_match:
                continue
            
            link_id = int(link_id_match.group(1))
            
            input_node_match = re.search(r'input\.node\.id\s+(\d+)', block)
            output_node_match = re.search(r'output\.node\.id\s+(\d+)', block)
            input_port_match = re.search(r'input\.port\.id\s+(\d+)', block)
            output_port_match = re.search(r'output\.port\.id\s+(\d+)', block)
            
            if not all([input_node_match, output_node_match, input_port_match, output_port_match]):
                continue
            
            links.append(PipeWireLink(
                id=link_id,
                input_node_id=int(input_node_match.group(1)),
                output_node_id=int(output_node_match.group(1)),
                input_port_id=int(input_port_match.group(1)),
                output_port_id=int(output_port_match.group(1)),
            ))
        
        return links
    
    async def set_volume(self, node_id: int, volume: float) -> bool:
        """Set volume for a node (0.0 to 1.0)"""
        try:
            # Use pw-cli to set volume
            cmd = [
                "pw-cli", "set-param", str(node_id),
                "props", json.dumps({"volume": volume})
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Failed to set volume: {stderr.decode()}")
                return False
            
            # Update local state
            if node_id in self._nodes:
                self._nodes[node_id].volume = volume
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return False
    
    async def set_mute(self, node_id: int, muted: bool) -> bool:
        """Set mute state for a node"""
        try:
            cmd = [
                "pw-cli", "set-param", str(node_id),
                "props", json.dumps({"mute": int(muted)})
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Failed to set mute: {stderr.decode()}")
                return False
            
            # Update local state
            if node_id in self._nodes:
                self._nodes[node_id].muted = muted
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set mute: {e}")
            return False
    
    async def move_source_to_channel(
        self, 
        source_id: str, 
        channel_sink_name: str
    ) -> bool:
        """
        Move an audio source to a specific channel (sink)
        
        This disconnects the source from its current sink and connects it to the new one.
        """
        try:
            # Find the source node
            source_node = None
            for node_id, node in self._nodes.items():
                if str(node_id) == source_id or node.name == source_id:
                    source_node = node
                    break
            
            if not source_node:
                logger.error(f"Source {source_id} not found")
                return False
            
            # Find the target sink
            target_sink = None
            for node_id, node in self._nodes.items():
                if node.name == channel_sink_name and node.node_type == PipeWireNodeType.SINK:
                    target_sink = node
                    break
            
            if not target_sink:
                logger.error(f"Sink {channel_sink_name} not found")
                return False
            
            # Disconnect existing links for this source
            await self._disconnect_source(source_node.id)
            
            # Connect to new sink
            return await self.connect_source_to_sink(
                str(source_node.id), 
                str(target_sink.id)
            )
            
        except Exception as e:
            logger.error(f"Failed to move source to channel: {e}")
            return False
    
    async def _disconnect_source(self, source_node_id: int) -> None:
        """Disconnect all links for a source node"""
        try:
            # Find all links where this node is the output
            links_to_remove = [
                link_id for link_id, link in self._links.items()
                if link.output_node_id == source_node_id
            ]
            
            for link_id in links_to_remove:
                cmd = ["pw-cli", "destroy", str(link_id)]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
            
            # Reload links
            await self._load_links()
            
        except Exception as e:
            logger.error(f"Failed to disconnect source: {e}")
    
    async def start_monitoring(self, interval: float = 1.0) -> None:
        """Start monitoring PipeWire for changes"""
        if self._monitor_task and not self._monitor_task.done():
            return
        
        async def monitor():
            while self._running:
                try:
                    await self._load_nodes()
                    await self._load_devices()
                    await self._load_links()
                    await self._update_sources_from_nodes()
                    
                    # Notify listeners
                    for listener in self._event_listeners:
                        try:
                            await listener("update", {"nodes": self._nodes, "sources": self._sources})
                        except Exception as e:
                            logger.error(f"Event listener error: {e}")
                    
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                
                await asyncio.sleep(interval)
        
        self._monitor_task = asyncio.create_task(monitor())
    
    def add_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Add an event listener for PipeWire changes"""
        self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Remove an event listener"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
    
    async def get_node_by_name(self, name: str) -> Optional[PipeWireNode]:
        """Get a node by its name"""
        for node in self._nodes.values():
            if node.name == name:
                return node
        return None
    
    async def get_device_by_name(self, name: str) -> Optional[AudioDevice]:
        """Get a device by its name"""
        for device in self._devices.values():
            if device.name == name:
                return device
        return None
