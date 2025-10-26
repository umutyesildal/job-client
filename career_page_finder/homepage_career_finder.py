"""
Homepage Career Finder - Scrapes website homepage to find career page links
Runs only when sitemap scraper couldn't find a career page
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urljoin, urlparse
from typing import Optional, List, Tuple
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('homepage_crawler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class HomepageCareerFinder:
    """Finds career pages by scraping homepage links"""
    
    # Career page URL patterns (in priority order)
    CAREER_PATTERNS = [
        (r'/career[s]?/?$', 1),           # Highest priority
        (r'/career[s]?/[^/]*$', 1),
        (r'/work/?$', 2),
        (r'/work-?with-?us/?$', 2),
        (r'/jobs?/?$', 3),
        (r'/jobs?/[^/]*$', 3),
        (r'/opportunities/?$', 4),
        (r'/hiring/?$', 5),
        (r'/open-?positions/?$', 6),
        (r'/join-?us/?$', 7),
        (r'/joinus/?$', 7),
        (r'/employment/?$', 8),
        (r'/vacancies/?$', 9),
    ]
    
    # Link text patterns to look for
    LINK_TEXT_PATTERNS = [
        r'\bcareers?\b',
        r'\bwork\s+with\s+us\b',
        r'\bjobs?\b',
        r'\bopportunities\b',
        r'\bhiring\b',
        r'\bopen\s+positions?\b',
        r'\bjoin\s+us\b',
        r'\bemployment\b',
        r'\bvacancies\b',
    ]
    
    # Exclude patterns (job listings, not main career pages)
    EXCLUDE_PATTERNS = [
        r'/position[s]?/\d',
        r'/job[s]?/\d',
        r'/career[s]?/\d',
        r'/opening[s]?/\d',
        r'/apply/',
        r'/application[s]?/',
        r'/blog/',
        r'/news/',
        r'/article[s]?/',
    ]
    
    def __init__(self, delay: float = 3.0, timeout: int = 15):
        """
        Initialize the finder
        
        Args:
            delay: Delay in seconds between requests
            timeout: Request timeout in seconds
        """
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def normalize_url(self, url: str) -> str:
        """Add https:// if scheme is missing"""
        if not url.startswith(('http://', 'https://')):
            return f'https://{url}'
        return url
    
    def is_valid_career_url(self, url: str) -> bool:
        """Check if URL is excluded (job listing)"""
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        return True
    
    def get_pattern_priority(self, url: str) -> Optional[int]:
        """
        Get priority of URL based on pattern match
        
        Args:
            url: URL to check
            
        Returns:
            Priority number (lower = higher priority) or None
        """
        url_lower = url.lower()
        for pattern, priority in self.CAREER_PATTERNS:
            if re.search(pattern, url_lower):
                if self.is_valid_career_url(url):
                    return priority
        return None
    
    def extract_links_from_homepage(self, website: str) -> List[Tuple[str, int]]:
        """
        Extract all career-related links from homepage
        
        Args:
            website: Website URL
            
        Returns:
            List of tuples (url, priority)
        """
        base_url = self.normalize_url(website)
        career_links = []
        
        try:
            logger.info(f"Fetching homepage: {base_url}")
            response = self.session.get(base_url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            
            # Wait a bit for any quick JS to execute (though we can't execute JS)
            time.sleep(1)
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Focus on footer first, then entire page
            footer = soup.find('footer') or soup.find(id=re.compile(r'footer', re.I)) or soup.find(class_=re.compile(r'footer', re.I))
            
            # Search in footer first
            if footer:
                logger.info("Searching in footer section...")
                footer_links = self._extract_career_links(footer, base_url)
                career_links.extend(footer_links)
            
            # If nothing found in footer, search entire page
            if not career_links:
                logger.info("Searching entire page...")
                page_links = self._extract_career_links(soup, base_url)
                career_links.extend(page_links)
            
            # Remove duplicates while preserving priority
            seen = set()
            unique_links = []
            for url, priority in career_links:
                if url not in seen:
                    seen.add(url)
                    unique_links.append((url, priority))
            
            logger.info(f"Found {len(unique_links)} potential career page(s)")
            
            return unique_links
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching {base_url}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for {base_url}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for {base_url}")
        except Exception as e:
            logger.error(f"Error fetching homepage {base_url}: {e}")
        
        return []
    
    def _extract_career_links(self, soup_section, base_url: str) -> List[Tuple[str, int]]:
        """
        Extract career links from a BeautifulSoup section
        
        Args:
            soup_section: BeautifulSoup object or section
            base_url: Base URL for resolving relative links
            
        Returns:
            List of tuples (url, priority)
        """
        career_links = []
        
        # Find all links
        all_links = soup_section.find_all('a', href=True)
        logger.debug(f"Checking {len(all_links)} links...")
        
        for link in all_links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True).lower()
            
            # Skip empty hrefs or anchors
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(base_url, href)
            
            # Check URL pattern
            priority = self.get_pattern_priority(absolute_url)
            
            if priority:
                logger.info(f"Found career link: {absolute_url} (priority: {priority})")
                career_links.append((absolute_url, priority))
                continue
            
            # Also check link text for career keywords
            for text_pattern in self.LINK_TEXT_PATTERNS:
                if re.search(text_pattern, link_text, re.IGNORECASE):
                    # Check if the href looks career-related
                    if self.is_valid_career_url(absolute_url):
                        logger.info(f"Found career link by text '{link_text}': {absolute_url}")
                        career_links.append((absolute_url, 10))  # Lower priority for text matches
                        break
        
        return career_links
    
    def select_best_career_page(self, career_links: List[Tuple[str, int]]) -> List[str]:
        """
        Select best career page(s) from list based on priority (max 2)
        
        Args:
            career_links: List of tuples (url, priority)
            
        Returns:
            List of career page URLs (maximum 2)
        """
        if not career_links:
            return []
        
        # Sort by priority (lower number = higher priority), then by URL length
        sorted_links = sorted(career_links, key=lambda x: (x[1], len(x[0])))
        
        # Return maximum 2 links with the best priorities
        best_links = [url for url, priority in sorted_links[:2]]
        
        logger.info(f"Selected {len(best_links)} career page(s)")
        return best_links
    
    def process_company(self, name: str, website: str) -> Tuple[str, str]:
        """
        Process a single company to find career page
        
        Args:
            name: Company name
            website: Company website
            
        Returns:
            Tuple of (career_page_urls, status)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {name} ({website})")
        logger.info(f"{'='*60}")
        
        if not website or pd.isna(website):
            logger.warning(f"No website provided for {name}")
            return "", "NO_WEBSITE"
        
        try:
            # Extract links from homepage
            career_links = self.extract_links_from_homepage(website)
            
            if not career_links:
                return "", "NOT_FOUND"
            
            # Select best career page(s)
            best_pages = self.select_best_career_page(career_links)
            
            if best_pages:
                # Join multiple URLs with semicolon
                result = "; ".join(best_pages)
                return result, "FOUND"
            else:
                return "", "NOT_FOUND"
                
        except Exception as e:
            logger.error(f"Error processing {name}: {e}")
            return "", "ERROR"
    
    def process_database(self, csv_path: str, output_path: str = None):
        """
        Process entire database CSV (only entries without career pages)
        
        Args:
            csv_path: Path to input CSV
            output_path: Path to output CSV (if None, updates input file)
        """
        logger.info(f"Loading database from {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Filter to only process entries without career pages
        empty_career_pages = df['Career Page'].isna() | (df['Career Page'] == '')
        companies_to_process = df[empty_career_pages]
        
        logger.info(f"Found {len(companies_to_process)} companies without career pages")
        
        if len(companies_to_process) == 0:
            logger.info("No companies to process!")
            return
        
        # Track statistics
        stats = {
            'found': 0,
            'not_found': 0,
            'errors': 0
        }
        
        # Process each company
        for idx, row in companies_to_process.iterrows():
            name = row['Name']
            website = row['Website']
            
            # Process company
            career_page, status = self.process_company(name, website)
            
            # Update dataframe
            if career_page:
                df.at[idx, 'Career Page'] = career_page
            
            # Update statistics
            if status == "FOUND":
                stats['found'] += 1
            elif status == "NOT_FOUND":
                stats['not_found'] += 1
            else:
                stats['errors'] += 1
            
            # Save progress after each company
            output = output_path or csv_path
            df.to_csv(output, index=False)
            logger.info(f"Progress saved to {output}")
            
            # Delay before next request
            time.sleep(self.delay)
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info("SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total processed: {len(companies_to_process)}")
        logger.info(f"Career pages found: {stats['found']}")
        logger.info(f"Not found: {stats['not_found']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info(f"{'='*60}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Find career pages by scraping homepage links')
    parser.add_argument('input', help='Input CSV file path')
    parser.add_argument('-o', '--output', help='Output CSV file path (default: updates input file)')
    parser.add_argument('-d', '--delay', type=float, default=3.0, help='Delay between requests (seconds)')
    parser.add_argument('-t', '--timeout', type=int, default=15, help='Request timeout (seconds)')
    
    args = parser.parse_args()
    
    # Create finder and process database
    finder = HomepageCareerFinder(delay=args.delay, timeout=args.timeout)
    finder.process_database(args.input, args.output)


if __name__ == '__main__':
    main()
