# vscan-server-banner-grabber

Retrieves the Server header (banner) of an HTTP target to identify the server software and version. Both target forms return the same thing: the value of the Server header.

How it works:

- A strict IPv4 literal target (for example 192.168.1.1) is contacted over a raw socket with an HTTP HEAD request. The response head is read until the end of the headers (up to 8192 bytes), so a banner split across packets is reassembled, and the Server header value is extracted from it. Shortened numeric forms such as 127.1 are not treated as IP literals; they take the hostname path.
- A hostname or URL target is contacted with an HTTP HEAD request. Redirects are not followed, so the banner reported is the one the requested target itself returned. For an https URL with no explicit port, port 443 is used; for http, port 80.
- Any userinfo in the target URL is stripped before the request is built and is never printed in the log.
- A reachable server that sends no Server header, and a server that cannot be reached, both exit non-zero, and the log lines separate the two cases (header not found versus connect or request failed).

## Install

`git clone https://github.com/ShadowGuard-AI/vscan-server-banner-grabber`

Requires Python 3 and the package in requirements.txt (requests).

## Usage

`python3 main.py TARGET [-p PORT] [-v] [-t TIMEOUT]`

Examples: `python3 main.py http://127.0.0.1:8080/` and `python3 main.py 127.0.0.1 -p 8080`

## Parameters

- `target`: Target URL or IP address (for example http://example.com or 192.168.1.1).
- `-h`: Show help message and exit
- `-p`, `--port`: Port number to connect to (default: 80, or 443 for an https URL, or the port in the target URL). Must be between 1 and 65535.
- `-v`, `--verbose`: Enable verbose output (debug logging).
- `-t`, `--timeout`: Timeout for requests in seconds (default: 5). Must be positive.

## License

MIT (see the LICENSE file)
