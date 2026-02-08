#!/usr/bin/env python3
"""
RavenProxyScraper - High-speed proxy harvesting tool for Proxychains
Scrapes proxies from multiple sources and formats them for Proxychains
"""

import requests
import re
import concurrent.futures
import argparse
import json
import os
import sys
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import socket
import threading
from queue import Queue
import configparser

# ASCII Art Banner
BANNER = """
██████╗  █████╗ ██╗   ██╗███████╗███╗   ██╗
██╔══██╗██╔══██╗██║   ██║██╔════╝████╗  ██║
██████╔╝███████║██║   ██║█████╗  ██╔██╗ ██║
██╔══██╗██╔══██║╚██╗ ██╔╝██╔══╝  ██║╚██╗██║
██║  ██║██║  ██║ ╚████╔╝ ███████╗██║ ╚████║
╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═══╝
███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗
██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝
╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║
╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝

[+] Fast as a Raven, Deadly as a Scavenger
[+] Scraping decaying proxies since 2024
[+] https://github.com/Sirhadey/raven-proxy-scraper
[+] https://twitter.com/adphily
[+] https://tiktok.com/adphily
[+] https://instagram.com/adphily
"""

class ProxyScraper:
    def __init__(self, config_file='raven.conf', user_agents_file='user_agents.txt'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.user_agents = []
        self.proxies = []
        self.valid_proxies = []
        self.load_config()
        self.load_user_agents(user_agents_file)

    def load_config(self):
        """Load configuration from file"""
        default_config = {
            'sites': {
                'urls': """
https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all
https://www.proxy-list.download/api/v1/get?type=socks5
https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt
https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt
https://spys.one/en/socks-proxy-list/
https://www.socks-proxy.net/
https://free-proxy-list.net/
https://www.sslproxies.org/
https://hidemy.name/en/proxy-list/
                """.strip(),
                'timeout': '10',
                'max_workers': '20'
            },
            'output': {
                'proxychains_file': 'proxychains.conf',
                'raw_file': 'proxies.txt',
                'json_file': 'proxies.json'
            },
            'validation': {
                'test_url': 'http://httpbin.org/ip',
                'timeout': '5',
                'max_validation_workers': '50'
            }
        }

        # Create config if doesn't exist
        if not os.path.exists(self.config_file):
            self.config.read_dict(default_config)
            with open(self.config_file, 'w') as f:
                self.config.write(f)
            print(f"[+] Created default configuration file: {self.config_file}")
        else:
            self.config.read(self.config_file)

        # Parse URLs from config
        self.site_urls = [url.strip() for url in
                         self.config['sites']['urls'].split('\n') if url.strip()]

    def load_user_agents(self, filename):
        """Load user agents from file or use defaults"""
        default_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

        if os.path.exists(filename):
            with open(filename, 'r') as f:
                self.user_agents = [line.strip() for line in f if line.strip()]
        else:
            self.user_agents = default_agents

    def get_random_headers(self):
        """Get random headers for requests"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def scrape_proxyscrape(self, url):
        """Scrape from ProxyScrape API"""
        try:
            response = requests.get(url, headers=self.get_random_headers(), timeout=10)
            if response.status_code == 200:
                proxies = response.text.strip().split('\n')
                return [{'ip': p.split(':')[0], 'port': p.split(':')[1], 'type': 'socks5'}
                        for p in proxies if ':' in p]
        except Exception as e:
            print(f"[-] Error scraping {url}: {e}")
        return []

    def scrape_spys_one(self, url):
        """Scrape from spys.one"""
        proxies = []
        try:
            response = requests.get(url, headers=self.get_random_headers(), timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for proxy table rows
            for row in soup.find_all('tr', class_='spy1xx'):
                cells = row.find_all('td')
                if len(cells) > 1:
                    script_tag = cells[0].find('script')
                    if script_tag:
                        script_text = script_tag.text
                        # Extract IP from JavaScript
                        ip_match = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', script_text)
                        port_match = re.search(r':(\d{2,5})', script_text)

                        if ip_match and port_match:
                            proxies.append({
                                'ip': ip_match.group(),
                                'port': port_match.group(1),
                                'type': 'socks5'
                            })
        except Exception as e:
            print(f"[-] Error scraping spys.one: {e}")
        return proxies

    def scrape_free_proxy_list(self, url):
        """Scrape from free-proxy-list.net"""
        proxies = []
        try:
            response = requests.get(url, headers=self.get_random_headers(), timeout=10)

            # Extract proxies from table
            pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td><td>(\d+)</td>'
            matches = re.findall(pattern, response.text)

            for ip, port in matches:
                proxies.append({
                    'ip': ip,
                    'port': port,
                    'type': 'http'  # Most are HTTP on this site
                })
        except Exception as e:
            print(f"[-] Error scraping free-proxy-list: {e}")
        return proxies

    def scrape_raw_list(self, url):
        """Scrape from raw text lists"""
        proxies = []
        try:
            response = requests.get(url, headers=self.get_random_headers(), timeout=10)
            lines = response.text.strip().split('\n')

            for line in lines:
                line = line.strip()
                if ':' in line:
                    ip, port = line.split(':', 1)
                    # Determine proxy type from URL
                    proxy_type = 'socks5' if 'socks5' in url.lower() else 'http'
                    proxies.append({
                        'ip': ip,
                        'port': port,
                        'type': proxy_type
                    })
        except Exception as e:
            print(f"[-] Error scraping raw list {url}: {e}")
        return proxies

    def scrape_site(self, url):
        """Route to appropriate scraper based on URL"""
        print(f"[+] Scraping: {url}")

        if 'proxyscrape' in url:
            return self.scrape_proxyscrape(url)
        elif 'spys.one' in url:
            return self.scrape_spys_one(url)
        elif 'free-proxy-list' in url or 'sslproxies' in url:
            return self.scrape_free_proxy_list(url)
        else:
            return self.scrape_raw_list(url)

    def validate_proxy(self, proxy, test_url=None):
        """Validate proxy by making a test request"""
        if test_url is None:
            test_url = self.config['validation']['test_url']

        proxies = {
            'http': f"{proxy['type']}://{proxy['ip']}:{proxy['port']}",
            'https': f"{proxy['type']}://{proxy['ip']}:{proxy['port']}"
        }

        try:
            timeout = int(self.config['validation']['timeout'])
            response = requests.get(test_url, proxies=proxies, timeout=timeout)

            if response.status_code == 200:
                proxy['response_time'] = response.elapsed.total_seconds()
                proxy['country'] = 'Unknown'  # Could add geoip lookup here
                proxy['validated_at'] = datetime.now().isoformat()
                return proxy
        except Exception:
            pass
        return None

    def scrape_all_sites(self):
        """Scrape all configured sites"""
        print("[+] Starting proxy scraping...")

        max_workers = int(self.config['sites']['max_workers'])

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.scrape_site, url): url for url in self.site_urls}

            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    proxies = future.result()
                    self.proxies.extend(proxies)
                    print(f"[+] Found {len(proxies)} proxies from {url}")
                except Exception as e:
                    print(f"[-] Error scraping {url}: {e}")

        # Remove duplicates
        unique_proxies = []
        seen = set()
        for proxy in self.proxies:
            key = (proxy['ip'], proxy['port'])
            if key not in seen:
                seen.add(key)
                unique_proxies.append(proxy)

        self.proxies = unique_proxies
        print(f"[+] Total unique proxies found: {len(self.proxies)}")

    def validate_all_proxies(self):
        """Validate all scraped proxies"""
        if not self.proxies:
            print("[-] No proxies to validate")
            return

        print(f"[+] Validating {len(self.proxies)} proxies...")

        max_workers = int(self.config['validation']['max_validation_workers'])
        test_url = self.config['validation']['test_url']

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.validate_proxy, proxy, test_url)
                      for proxy in self.proxies]

            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                result = future.result()
                if result:
                    self.valid_proxies.append(result)

                # Progress indicator
                if (i + 1) % 50 == 0:
                    print(f"[+] Validated {i + 1}/{len(self.proxies)} proxies...")

        print(f"[+] Valid proxies: {len(self.valid_proxies)}/{len(self.proxies)}")

    def format_for_proxychains(self):
        """Format proxies for Proxychains configuration"""
        lines = []
        lines.append("# Proxychains configuration file")
        lines.append("# Generated by RavenProxyScraper")
        lines.append(f"# Generated on: {datetime.now().isoformat()}")
        lines.append("")
        lines.append("[ProxyList]")
        lines.append("# add proxy here ...")
        lines.append("# meanwhile")
        lines.append("# defaults set to \"tor\"")
        lines.append("")

        for proxy in self.valid_proxies:
            if proxy['type'] in ['socks4', 'socks5']:
                line = f"{proxy['type']} {proxy['ip']} {proxy['port']}"
                if 'response_time' in proxy:
                    line += f" # {proxy['response_time']:.2f}s"
                lines.append(line)

        return '\n'.join(lines)

    def save_output(self):
        """Save all output files"""
        output_dir = self.config['output']

        # Save raw proxies
        with open(output_dir['raw_file'], 'w') as f:
            for proxy in self.proxies:
                f.write(f"{proxy['ip']}:{proxy['port']}\n")

        # Save JSON data
        with open(output_dir['json_file'], 'w') as f:
            json.dump({
                'total_found': len(self.proxies),
                'valid': len(self.valid_proxies),
                'proxies': self.valid_proxies,
                'generated_at': datetime.now().isoformat()
            }, f, indent=2)

        # Save Proxychains config
        proxychains_config = self.format_for_proxychains()
        with open(output_dir['proxychains_file'], 'w') as f:
            f.write(proxychains_config)

        print(f"[+] Saved {len(self.proxies)} proxies to {output_dir['raw_file']}")
        print(f"[+] Saved {len(self.valid_proxies)} valid proxies to {output_dir['json_file']}")
        print(f"[+] Saved Proxychains config to {output_dir['proxychains_file']}")

        # Display sample
        print("\n[+] Sample of valid proxies:")
        for i, proxy in enumerate(self.valid_proxies[:5]):
            print(f"  {i+1}. {proxy['type']}://{proxy['ip']}:{proxy['port']}")

    def add_custom_sites(self, sites_file):
        """Add custom sites from a text file"""
        if not os.path.exists(sites_file):
            print(f"[-] File not found: {sites_file}")
            return False

        with open(sites_file, 'r') as f:
            new_sites = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        # Update config
        current_sites = self.site_urls
        current_sites.extend(new_sites)

        # Remove duplicates
        self.site_urls = list(dict.fromkeys(current_sites))

        # Save to config file
        self.config['sites']['urls'] = '\n'.join(self.site_urls)
        with open(self.config_file, 'w') as f:
            self.config.write(f)

        print(f"[+] Added {len(new_sites)} new sites to configuration")
        return True

    def run(self, validate=True, custom_sites=None):
        """Main execution method"""
        print(BANNER)

        # Add custom sites if specified
        if custom_sites:
            self.add_custom_sites(custom_sites)

        # Scrape proxies
        self.scrape_all_sites()

        # Validate proxies
        if validate and self.proxies:
            self.validate_all_proxies()
        else:
            self.valid_proxies = self.proxies

        # Save results
        if self.proxies:
            self.save_output()
        else:
            print("[-] No proxies found!")

def main():
    parser = argparse.ArgumentParser(
        description="RavenProxyScraper - High-speed proxy harvesting tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run with default configuration
  %(prog)s -c custom.conf           # Use custom configuration file
  %(prog)s --no-validate            # Skip proxy validation (faster)
  %(prog)s --add-sites sites.txt    # Add custom sites from file
  %(prog)s --list-sites             # List all configured sites
  %(prog)s --test-url "http://ifconfig.me"  # Use custom test URL
        """
    )

    parser.add_argument('-c', '--config', default='raven.conf',
                       help='Configuration file (default: raven.conf)')
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip proxy validation (much faster)')
    parser.add_argument('--add-sites', metavar='FILE',
                       help='Add custom sites from text file')
    parser.add_argument('--list-sites', action='store_true',
                       help='List all configured scraping sites')
    parser.add_argument('--test-url', metavar='URL',
                       help='Custom URL for proxy validation')
    parser.add_argument('-o', '--output', metavar='FILE',
                       help='Custom output file for Proxychains config')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    # Initialize scraper
    scraper = ProxyScraper(config_file=args.config)

    # List sites if requested
    if args.list_sites:
        print("[+] Configured scraping sites:")
        for i, url in enumerate(scraper.site_urls, 1):
            print(f"  {i}. {url}")
        return

    # Update test URL if specified
    if args.test_url:
        scraper.config['validation']['test_url'] = args.test_url

    # Update output file if specified
    if args.output:
        scraper.config['output']['proxychains_file'] = args.output

    # Run the scraper
    scraper.run(
        validate=not args.no_validate,
        custom_sites=args.add_sites
    )

if __name__ == "__main__":
    main()
