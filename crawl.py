from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import os

load_dotenv()

fc_api_key = os.getenv("FIRECRAWL_API")

app = FirecrawlApp(api_key=fc_api_key)

def scrape_website(domain, max_pages=5):
    """
    domain: 'neosync.com' or similar
    max_pages: limit the number of pages to crawl
    returns: concatenated text from all crawled pages
    """
    scrape_result = app.scrape_url(
    domain, 
    params={'formats': ['markdown']}
    )
    print(scrape_result)
    
    return " ".join(scrape_result)

    