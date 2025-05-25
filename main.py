import argparse
import requests
import logging
import socket
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(description='vscan-server-banner-grabber: Retrieves server banners to identify software versions.')
    parser.add_argument('target', help='Target URL or IP address (e.g., http://example.com or 192.168.1.1)')
    parser.add_argument('-p', '--port', type=int, default=80, help='Port number to connect to (default: 80)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output (debug logging)')
    parser.add_argument('-t', '--timeout', type=int, default=5, help='Timeout for requests in seconds (default: 5)')
    return parser.parse_args()

def grab_banner(target, port, timeout):
    """
    Grabs the server banner from the target.
    """
    try:
        # Attempt to connect using sockets if it's an IP
        try:
            socket.inet_aton(target)
            # It's a valid IP address
            logging.info(f"Target is an IP Address: {target}")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((target, port))
                s.send(b"HEAD / HTTP/1.1\r\nHost: " + target.encode() + b"\r\n\r\n")
                banner = s.recv(1024).decode('utf-8', errors='ignore')  # Decode the banner, ignoring errors
                return banner
        except socket.error as e:
            #If IP fails, try URL instead
            logging.debug(f"Socket connection to IP failed: {e}. Trying as URL.")
            # Try to parse the URL to make a request
            parsed_url = urlparse(target)
            if not parsed_url.scheme:
                target = "http://" + target # Add default scheme if missing
            
            logging.info(f"Trying URL: {target}")
            response = requests.head(target, timeout=timeout, allow_redirects=True)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            
            # Extract the server header
            if 'Server' in response.headers:
                return response.headers['Server']
            else:
                logging.info("Server header not found in HTTP response.")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
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
        logging.info("Failed to retrieve server banner.")

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