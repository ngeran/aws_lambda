import socket
from jnpr.junos import Device
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_reachable(hostname, port=22, timeout=5):
    """
    Check if a host is reachable by attempting a socket connection.

    Args:
        hostname (str): The hostname or IP address to check
        port (int): Port to test (default: 22 for SSH)
        timeout (int): Socket timeout in seconds

    Returns:
        bool: True if reachable, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((hostname, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking reachability for {hostname}: {str(e)}")
        return False

def connect_to_device(hostname, username, password):
    """
    Establish a connection to a Junos device.

    Args:
        hostname (str): Device hostname or IP
        username (str): Login username
        password (str): Login password

    Returns:
        Device: Connected Junos Device object if successful, None otherwise
    """
    try:
        device = Device(host=hostname, user=username, password=password)
        device.open()
        logger.info(f"Successfully connected to {hostname}")
        return device
    except Exception as e:
        logger.error(f"Failed to connect to {hostname}: {str(e)}")
        return None
