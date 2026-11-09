import argparse
import ipaddress
import requests
import logging
import socket
import sys
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(description='vscan-server-banner-grabber: Retrieves server banners to identify software versions.')
    parser.add_argument('target', help='Target URL or IP address (e.g., http://example.com or 192.168.1.1)')
    parser.add_argument('-p', '--port', type=int, default=None, help='Port number to connect to (default: 80, or the port in the target URL)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output (debug logging)')
    parser.add_argument('-t', '--timeout', type=int, default=5, help='Timeout for requests in seconds (default: 5)')
    return parser.parse_args()

def _server_header_from_head(head):
    """Return the Server header value from a raw HTTP response head, or None."""
    for line in head.splitlines():
        if line.lower().startswith("server:"):
            return line.split(":", 1)[1].strip()
    return None

def grab_banner(target, port, timeout):
    """
    Grabs the Server banner from the target. Both the IP literal path and
    the hostname or URL path return the same thing: the value of the
    Server header, or None when no banner could be retrieved. The log
    separates the reasons: connection failure, request failure, and a
    reachable server that sent no Server header.
    """
    # Strict IPv4 literal test. Shortened forms such as 127.1 are not
    # accepted as IP literals; they take the hostname or URL path below.
    is_ip = False
    try:
        ipaddress.IPv4Address(target)
        is_ip = True
    except ValueError:
        is_ip = False

    try:
        if is_ip:
            effective_port = port if port is not None else 80
            logging.info(f"Target is an IP Address: {target}")
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    s.connect((target, effective_port))
                    s.send(b"HEAD / HTTP/1.1\r\nHost: " + target.encode() + b"\r\n\r\n")
                    # Read until the end of the response head, EOF, or an
                    # 8192 byte cap, so a banner split across packets is
                    # reassembled instead of cut at the first packet.
                    chunks = []
                    total = 0
                    while total < 8192:
                        chunk = s.recv(4096)
                        if not chunk:
                            break
                        chunks.append(chunk)
                        total += len(chunk)
                        if b"\r\n\r\n" in b"".join(chunks):
                            break
                    head = b"".join(chunks).decode('utf-8', errors='ignore')
            except (socket.error, OSError) as e:
                logging.error(f"Connect failed for IP target {target}:{effective_port}: {e}")
                return None
            banner = _server_header_from_head(head)
            if banner:
                return banner
            logging.info("Server header not found in raw response from IP target.")
            return None

        # Hostname or URL path: apply the requested port.
        raw = target if urlparse(target).scheme else "http://" + target
        parsed_url = urlparse(raw)
        if parsed_url.scheme not in ("http", "https"):
            logging.error(f"Invalid target scheme: {parsed_url.scheme} (only http and https are supported)")
            return None
        effective_port = port if port is not None else (parsed_url.port or (443 if parsed_url.scheme == "https" else 80))
        host = parsed_url.hostname or ""
        # The rebuilt netloc never carries userinfo, so a password in the
        # original target is neither sent nor printed in the log line.
        netloc = f"[{host}]:{effective_port}" if ":" in host else f"{host}:{effective_port}"
        url_with_port = parsed_url._replace(netloc=netloc).geturl()
        logging.info(f"Trying URL: {url_with_port}")
        try:
            # Redirects are not followed: the banner reported is the one
            # the requested target itself returned, not the banner of
            # wherever a redirect chain would have landed.
            response = requests.head(url_with_port, timeout=timeout, allow_redirects=False)
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            return None
        # Error responses are responses: read the banner before any status check.
        logging.info(f"Response status: {response.status_code}")
        if 'Server' in response.headers:
            return response.headers['Server']
        logging.info("Server header not found in HTTP response.")
        return None



    except ValueError as e:
        logging.error(f"Invalid target: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

def main():
    """
    Main function to execute the banner grabbing process.
    """
    args = setup_argparse()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)  # Set logging level to DEBUG if verbose is enabled

    if args.port is not None and not (1 <= args.port <= 65535):
        logging.error("Port must be between 1 and 65535.")
        sys.exit(2)

    if args.timeout <= 0:
        logging.error("Timeout must be positive.")
        sys.exit(2)

    # Log a userinfo-free form of the target, so a password embedded in a
    # URL target never lands in a log.
    _parsed = urlparse(args.target if urlparse(args.target).scheme else "http://" + args.target)
    _display = _parsed._replace(netloc=_parsed.netloc.rsplit("@", 1)[-1]).geturl() if "@" in _parsed.netloc else args.target
    logging.info(f"Starting banner grabbing for {_display} (port: {args.port if args.port is not None else 'default'})")

    banner = grab_banner(args.target, args.port, args.timeout)

    if banner:
        print(f"Server Banner: {banner}")
        logging.info(f"Server Banner: {banner}")
    else:
        print("Failed to retrieve server banner.")
        logging.error("Failed to retrieve server banner.")
        sys.exit(1)

if __name__ == "__main__":
    main()


"""
Usage Examples:

1.  Basic usage to grab banner from a website:
    python main.py http://example.com

2.  Specify a port number:
    python main.py example.com -p 8080

3.  Enable verbose output for debugging:
    python main.py example.com -v

4.  Set a custom timeout value:
    python main.py example.com -t 10

5. Target IP address:
    python main.py 127.0.0.1
"""
