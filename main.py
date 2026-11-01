import argparse
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

def grab_banner(target, port, timeout):
    """
    Grabs the server banner from the target.
    """
    # Decide whether the target is an IP literal first. That test is
    # separate from whether a connection to it succeeds.
    is_ip = False
    try:
        # inet_aton decides the whole shape of this tool and it is a loose judge. It accepts shortened numeric forms like 127.1 as an address, so a target can be treated as an IP that a person would read as a name, and then it gets the raw socket treatment below instead of the HTTP one.
        socket.inet_aton(target)
        is_ip = True
    except (socket.error, OSError):
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
                    # One read of up to 1024 bytes is the whole grab on this path. A banner that arrives in two packets, or a slow greeting protocol that sends nothing until it is spoken to, comes back empty or cut, and the decode drops any byte that is not clean UTF-8.
                    banner = s.recv(1024).decode('utf-8', errors='ignore')
                    # The two paths in this function do not return the same kind of thing. An IP target returns the whole response head, status line and every header, while a named target below returns only the Server value, and main prints both under the same Server Banner label.
                    return banner if banner else None
            except (socket.error, OSError) as e:
                logging.error(f"Connect failed for IP target {target}:{effective_port}: {e}")
                return None

        # Hostname or URL path: apply the requested port.
        raw = target if urlparse(target).scheme else "http://" + target
        parsed_url = urlparse(raw)
        effective_port = port if port is not None else (parsed_url.port or 80)
        host = parsed_url.hostname or ""
        # Rebuilding the netloc puts the port in even when the caller never wrote one, and the line above it carries any userinfo from the original URL into the rebuilt one, password included. The log line below then prints that rebuilt address, credentials and all, so I would not share a verbose log from a run against an authenticated address.
        netloc = f"{host}:{effective_port}"
        if parsed_url.username:
            netloc = parsed_url.username + (":" + parsed_url.password if parsed_url.password else "") + "@" + netloc
        url_with_port = parsed_url._replace(netloc=netloc).geturl()
        logging.info(f"Trying URL: {url_with_port}")
        try:
            # Following redirects on a HEAD means the banner belongs to wherever the chain lands. A front end that redirects to a different stack reports that stacks Server header under the original targets name.
            response = requests.head(url_with_port, timeout=timeout, allow_redirects=True)
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            return None
        # Error responses are responses: read the banner before any status check.
        logging.info(f"Response status: {response.status_code}")
        # A server that sends no Server header and a server that cannot be reached both end as None here or above, and main prints the same failure line for both. Nothing in the output separates a quiet server from a dead one.
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

    logging.info(f"Starting banner grabbing for {args.target}:{args.port}")

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
    python main.py http://example.com -v

4.  Set a custom timeout value:
    python main.py http://example.com -t 10

5. Target IP address:
    python main.py 127.0.0.1
"""
