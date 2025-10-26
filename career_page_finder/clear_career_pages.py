"""
Clear Career Pages - Remove all career page entries from Database
"""

import pandas as pd
import sys


def clear_career_pages(csv_path: str):
    """
    Clear all career page entries from the CSV file
    
    Args:
        csv_path: Path to the CSV file
    """
    print(f"Loading database from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Count how many have career pages
    filled_count = df['Career Page'].notna().sum()
    print(f"Found {filled_count} entries with career pages")
    
    # Clear the Career Page column
    df['Career Page'] = ""
    
    # Save back to file
    df.to_csv(csv_path, index=False)
    print(f"✓ Cleared all career pages and saved to {csv_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 clear_career_pages.py <csv_file>")
        print("Example: python3 clear_career_pages.py Database.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    
    # Confirm with user
    response = input(f"Are you sure you want to clear all career pages from {csv_path}? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        clear_career_pages(csv_path)
    else:
        print("Operation cancelled.")


if __name__ == '__main__':
    main()
