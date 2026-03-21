"""mDNS Network Discovery Service for Agent Zoo."""

import logging
import threading
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Try to import zeroconf, with graceful fallback
try:
    import zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    logger.warning("python-zeroconf not installed. Network discovery will be disabled.")


SERVICE_TYPE = "_agent._tcp.local."
DEFAULT_PORT = 8001


@dataclass
class NetworkAgent:
    """Data model for a discovered agent on the network."""

    source: str = "network"  # always "network"
    name: str = ""  # e.g., "agent-zoo.local"
    address: str = ""  # IP address
    port: int = DEFAULT_PORT  # Agent Zoo port
    version: str = "1.0.0"
    capabilities: List[str] = field(default_factory=list)

    @classmethod
    def from_zeroconf_info(cls, name: str, address: str, port: int, properties: dict) -> "NetworkAgent":
        """Create a NetworkAgent from zeroconf service info."""
        return cls(
            source="network",
            name=name,
            address=address,
            port=port,
            version=properties.get("version", "1.0.0"),
            capabilities=properties.get("capabilities", "").split(",") if properties.get("capabilities") else [],
        )


class NetworkDiscoveryService:
    """mDNS Network Discovery Service for discovering Agent Zoo instances on local network."""

    def __init__(self):
        """Initialize the network discovery service."""
        self._zc: Optional[zeroconf.Zeroconf] = None
        self._browser: Optional[zeroconf.ServiceBrowser] = None
        self._discovered_agents: List[NetworkAgent] = []
        self._lock = threading.Lock()
        self._is_browsing = False

        if not ZEROCONF_AVAILABLE:
            logger.warning("NetworkDiscoveryService: zeroconf not available")
            return

        self._zc = zeroconf.Zeroconf()

    def start_browsing(self) -> bool:
        """
        Begin discovering _agent._tcp.local. services.

        Returns:
            True if browsing started successfully, False otherwise.
        """
        if not ZEROCONF_AVAILABLE or self._zc is None:
            logger.warning("start_browsing: zeroconf not available")
            return False

        if self._is_browsing:
            logger.info("start_browsing: already browsing")
            return True

        try:
            self._browser = zeroconf.ServiceBrowser(
                self._zc,
                SERVICE_TYPE,
                handlers=[self._on_service_state_change]
            )
            self._is_browsing = True
            logger.info("start_browsing: started browsing for %s", SERVICE_TYPE)
            return True
        except Exception as e:
            logger.error("start_browsing: failed to start browsing: %s", e)
            return False

    def stop_browsing(self) -> None:
        """Stop discovery."""
        self._is_browsing = False
        with self._lock:
            self._discovered_agents.clear()

        if self._browser is not None:
            try:
                self._browser.cancel()
            except Exception as e:
                logger.debug("stop_browsing: error canceling browser: %s", e)
            self._browser = None

        logger.info("stop_browsing: stopped browsing")

    def get_discovered_agents(self) -> List[NetworkAgent]:
        """
        Return list of discovered agents.

        Returns:
            List of NetworkAgent instances discovered on the network.
        """
        with self._lock:
            return list(self._discovered_agents)

    def register_service(self, name: str, port: int = DEFAULT_PORT) -> bool:
        """
        Advertise this Agent Zoo instance via mDNS.

        Args:
            name: Service instance name (e.g., "agent-zoo")
            port: Port number for the service

        Returns:
            True if registration succeeded, False otherwise.
        """
        if not ZEROCONF_AVAILABLE or self._zc is None:
            logger.warning("register_service: zeroconf not available")
            return False

        try:
            desc = {"version": "1.0.0", "capabilities": ""}
            info = zeroconf.ServiceInfo(
                SERVICE_TYPE,
                f"{name}.{SERVICE_TYPE}",
                addresses=[],
                port=port,
                properties=desc,
            )
            self._zc.register_service(info)
            logger.info("register_service: registered %s on port %d", name, port)
            return True
        except Exception as e:
            logger.error("register_service: failed to register service: %s", e)
            return False

    def unregister_service(self, name: str) -> None:
        """
        Unadvertise this Agent Zoo instance.

        Args:
            name: Service instance name to unregister.
        """
        if not ZEROCONF_AVAILABLE or self._zc is None:
            return

        try:
            info = zeroconf.ServiceInfo(
                SERVICE_TYPE,
                f"{name}.{SERVICE_TYPE}",
                addresses=[],
                port=0,
                properties={},
            )
            self._zc.unregister_service(info)
            logger.info("unregister_service: unregistered %s", name)
        except Exception as e:
            logger.debug("unregister_service: error unregistering: %s", e)

    def _on_service_state_change(
        self,
        zc: zeroconf.Zeroconf,
        service_type: str,
        name: str,
        state: str
    ) -> None:
        """Handle service state changes from zeroconf."""
        if state == zeroconf.ServiceStateChange.Added:
            self._add_service(name)
        elif state == zeroconf.ServiceStateChange.Removed:
            self._remove_service(name)

    def _add_service(self, name: str) -> None:
        """Add a discovered service."""
        try:
            if self._zc is None:
                return
            info = self._zc.get_service_info(SERVICE_TYPE, name)
            if info is None:
                return

            # Parse addresses
            addresses = []
            for addr in info.addresses:
                if len(addr) == 4:
                    # IPv4
                    addresses.append(".".join(str(b) for b in addr))
                elif len(addr) == 16:
                    # IPv6 - skip for now
                    continue

            address = addresses[0] if addresses else ""
            port = info.port

            # Parse properties
            properties = {}
            for key, value in info.properties.items():
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                properties[key] = value

            agent = NetworkAgent.from_zeroconf_info(
                name=name.replace(f".{SERVICE_TYPE}", ""),
                address=address,
                port=port,
                properties=properties,
            )

            with self._lock:
                # Avoid duplicates
                existing = [a for a in self._discovered_agents if a.name == agent.name]
                if not existing:
                    self._discovered_agents.append(agent)
                    logger.info("_add_service: discovered %s at %s:%d", agent.name, agent.address, agent.port)

        except Exception as e:
            logger.error("_add_service: error adding service %s: %s", name, e)

    def _remove_service(self, name: str) -> None:
        """Remove a service that is no longer available."""
        with self._lock:
            self._discovered_agents = [
                a for a in self._discovered_agents
                if a.name != name.replace(f".{SERVICE_TYPE}", "")
            ]
        logger.info("_remove_service: removed %s", name)

    def close(self) -> None:
        """Clean up resources."""
        self.stop_browsing()
        if self._zc is not None:
            try:
                self._zc.close()
            except Exception as e:
                logger.debug("close: error closing zeroconf: %s", e)
            self._zc = None

    def __del__(self) -> None:
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self) -> "NetworkDiscoveryService":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
