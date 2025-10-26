"""
Job Crawler - Career Page Finder
Searches company sitemaps for career page URLs
"""

import pandas as pd
import requests
import xml.etree.ElementTree as ET
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
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class CareerPageFinder:
    """Finds career pages by checking website sitemaps"""
    
    # Career page URL patterns to search for
    CAREER_PATTERNS = [
        r'/career[s]?/?$',
        r'/career[s]?/[^/]*$',
        r'/jobs?/?$',
        r'/jobs?/[^/]*$',
        r'/work/?$',
        r'/work-?with-?us/?$',
        r'/join-?us/?$',
        r'/joinus/?$',
        r'/opportunities/?$',
        r'/hiring/?$',
        r'/open-?positions/?$',
        r'/team/?$',
        r'/employment/?$',
        r'/vacancies/?$',
    ]
    
    # Patterns for career-related sitemap filenames
    CAREER_SITEMAP_PATTERNS = [
        r'career[s]?',
        r'jobs?',
        r'work',
        r'hiring',
        r'opportunities',
        r'employment',
        r'vacancies',
    ]
    
    # Patterns to exclude (job listings, not main career pages)
    EXCLUDE_PATTERNS = [
        r'/position[s]?/',
        r'/job[s]?/\d',
        r'/career[s]?/\d',
        r'/opening[s]?/',
        r'/apply/',
        r'/application[s]?/',
    ]
    
    # Sitemap locations to check
    SITEMAP_PATHS = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/sitemap-index.xml',
        '/sitemap1.xml',
    ]
    
    def __init__(self, delay: float = 2.0, timeout: int = 10):
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
            'User-Agent': 'Mozilla/5.0 (compatible; CareerPageBot/1.0)'
        })
    
    def normalize_url(self, url: str) -> str:
        """Add http:// if scheme is missing"""
        if not url.startswith(('http://', 'https://')):
            return f'https://{url}'
        return url
    
    def find_sitemap(self, website: str) -> Optional[str]:
        """
        Try to find a valid sitemap URL for the website
        
        Args:
            website: Base website URL
            
        Returns:
            URL of found sitemap or None
        """
        base_url = self.normalize_url(website)
        
        for path in self.SITEMAP_PATHS:
            sitemap_url = urljoin(base_url, path)
            try:
                logger.info(f"Checking sitemap: {sitemap_url}")
                response = self.session.get(sitemap_url, timeout=self.timeout)
                
                if response.status_code == 200 and 'xml' in response.headers.get('content-type', '').lower():
                    logger.info(f"✓ Found sitemap: {sitemap_url}")
                    return sitemap_url
                    
            except requests.exceptions.RequestException as e:
                logger.debug(f"Failed to fetch {sitemap_url}: {e}")
                continue
        
        logger.warning(f"No sitemap found for {website}")
        return None
    
    def is_career_sitemap(self, sitemap_url: str) -> bool:
        """
        Check if a sitemap URL is career-related based on filename
        
        Args:
            sitemap_url: URL of the sitemap
            
        Returns:
            True if sitemap appears to be career-related
        """
        url_lower = sitemap_url.lower()
        for pattern in self.CAREER_SITEMAP_PATTERNS:
            if re.search(pattern, url_lower):
                logger.info(f"Detected career-related sitemap: {sitemap_url}")
                return True
        return False
    
    def extract_base_career_url(self, urls: List[str]) -> Optional[str]:
        """
        Extract the base career page URL from a list (avoiding job listings)
        
        Args:
            urls: List of URLs from a career sitemap
            
        Returns:
            Base career page URL or None
        """
        # Filter out job listing URLs
        filtered_urls = []
        for url in urls:
            # Skip if matches exclude patterns (job listings)
            is_excluded = False
            for pattern in self.EXCLUDE_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    is_excluded = True
                    break
            
            if not is_excluded:
                # Check if it matches career patterns
                for pattern in self.CAREER_PATTERNS:
                    if re.search(pattern, url, re.IGNORECASE):
                        filtered_urls.append(url)
                        break
        
        if filtered_urls:
            # Return the shortest URL (usually the main career page)
            base_url = min(filtered_urls, key=len)
            logger.info(f"Selected base career URL: {base_url}")
            return base_url
        
        return None
    
    def parse_sitemap(self, sitemap_url: str, is_career_sitemap: bool = False) -> List[str]:
        """
        Parse sitemap XML and extract all URLs
        
        Args:
            sitemap_url: URL of the sitemap
            is_career_sitemap: Whether this is a known career sitemap
            
        Returns:
            List of URLs found in sitemap
        """
        urls = []
        
        try:
            response = self.session.get(sitemap_url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Handle namespace
            namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Check if this is a sitemap index (contains other sitemaps)
            sitemap_elements = root.findall('.//sm:sitemap/sm:loc', namespace)
            
            if sitemap_elements:
                # This is a sitemap index
                logger.info(f"Found sitemap index with {len(sitemap_elements)} sitemaps")
                
                # First, check if any child sitemap is career-related
                career_sitemap_found = False
                for elem in sitemap_elements:
                    child_sitemap_url = elem.text
                    if child_sitemap_url and self.is_career_sitemap(child_sitemap_url):
                        # Parse this career sitemap specifically
                        logger.info(f"Parsing career sitemap: {child_sitemap_url}")
                        career_urls = self.parse_sitemap(child_sitemap_url, is_career_sitemap=True)
                        
                        # Extract base career page
                        base_url = self.extract_base_career_url(career_urls)
                        if base_url:
                            return [base_url]  # Return early with the base career URL
                        
                        career_sitemap_found = True
                        break
                
                # If no career sitemap found, parse first few sitemaps
                if not career_sitemap_found:
                    for elem in sitemap_elements[:5]:  # Limit to first 5 sitemaps
                        child_sitemap_url = elem.text
                        if child_sitemap_url:
                            urls.extend(self.parse_sitemap(child_sitemap_url))
                            time.sleep(self.delay / 2)  # Shorter delay for same domain
            else:
                # Regular sitemap with URLs
                url_elements = root.findall('.//sm:url/sm:loc', namespace)
                urls = [elem.text for elem in url_elements if elem.text]
                logger.info(f"Extracted {len(urls)} URLs from sitemap")
                
        except Exception as e:
            logger.error(f"Error parsing sitemap {sitemap_url}: {e}")
        
        return urls
    
    def find_career_page(self, urls: List[str]) -> Optional[str]:
        """
        Search for career page URLs in the list
        
        Args:
            urls: List of URLs to search
            
        Returns:
            First matching career page URL or None
        """
        # Filter out job listings first
        potential_career_pages = []
        
        for url in urls:
            # Skip if matches exclude patterns
            is_excluded = False
            for pattern in self.EXCLUDE_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    is_excluded = True
                    break
            
            if is_excluded:
                continue
            
            # Check if matches career patterns
            url_lower = url.lower()
            for pattern in self.CAREER_PATTERNS:
                if re.search(pattern, url_lower):
                    potential_career_pages.append(url)
                    break
        
        # Return the shortest URL (likely the main career page, not a subpage)
        if potential_career_pages:
            career_page = min(potential_career_pages, key=len)
            logger.info(f"✓ Found career page: {career_page}")
            return career_page
        
        return None
    
    def process_company(self, name: str, website: str) -> Tuple[str, str]:
        """
        Process a single company to find career page
        
        Args:
            name: Company name
            website: Company website
            
        Returns:
            Tuple of (career_page_url, status)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {name} ({website})")
        logger.info(f"{'='*60}")
        
        if not website or pd.isna(website):
            logger.warning(f"No website provided for {name}")
            return "", "NO_WEBSITE"
        
        try:
            # Find sitemap
            sitemap_url = self.find_sitemap(website)
            if not sitemap_url:
                return "", "NO_SITEMAP"
            
            # Parse sitemap
            urls = self.parse_sitemap(sitemap_url)
            if not urls:
                return "", "EMPTY_SITEMAP"
            
            # Search for career page
            career_page = self.find_career_page(urls)
            if career_page:
                return career_page, "FOUND"
            else:
                return "", "NOT_FOUND"
                
        except Exception as e:
            logger.error(f"Error processing {name}: {e}")
            return "", "ERROR"
    
    def process_database(self, csv_path: str, output_path: str = None):
        """
        Process entire database CSV
        
        Args:
            csv_path: Path to input CSV
            output_path: Path to output CSV (if None, updates input file)
        """
        logger.info(f"Loading database from {csv_path}")
        df = pd.read_csv(csv_path)
        
        logger.info(f"Found {len(df)} companies to process")
        
        # Track statistics
        stats = {
            'found': 0,
            'not_found': 0,
            'no_sitemap': 0,
            'errors': 0
        }
        
        # Process each company
        for idx, row in df.iterrows():
            name = row['Name']
            website = row['Website']
            
            # Skip if career page already exists
            if pd.notna(row.get('Career Page')) and row['Career Page']:
                logger.info(f"Skipping {name} - career page already exists")
                continue
            
            # Process company
            career_page, status = self.process_company(name, website)
            
            # Update dataframe
            df.at[idx, 'Career Page'] = career_page if career_page else ""
            
            # Update statistics
            if status == "FOUND":
                stats['found'] += 1
            elif status == "NOT_FOUND":
                stats['not_found'] += 1
            elif status == "NO_SITEMAP":
                stats['no_sitemap'] += 1
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
        logger.info(f"Total processed: {len(df)}")
        logger.info(f"Career pages found: {stats['found']}")
        logger.info(f"No career page: {stats['not_found']}")
        logger.info(f"No sitemap: {stats['no_sitemap']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info(f"{'='*60}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Find career pages from company sitemaps')
    parser.add_argument('input', help='Input CSV file path')
    parser.add_argument('-o', '--output', help='Output CSV file path (default: updates input file)')
    parser.add_argument('-d', '--delay', type=float, default=2.0, help='Delay between requests (seconds)')
    parser.add_argument('-t', '--timeout', type=int, default=10, help='Request timeout (seconds)')
    
    args = parser.parse_args()
    
    # Create finder and process database
    finder = CareerPageFinder(delay=args.delay, timeout=args.timeout)
    finder.process_database(args.input, args.output)


if __name__ == '__main__':
    main()
