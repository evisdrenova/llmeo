from llms import call_openai, call_perplexity, call_claude,parse_openai_response,find_rank_in_tools
from dotenv import load_dotenv
from mdtext import md_text
from fpdf import FPDF
import re
import asyncio
from tqdm import tqdm
from crawl import scrape_website
import json
import traceback
from pdf import generate_pdf_report

load_dotenv()

domain = "https://www.neosync.dev"


llm_clients = []


def extract_keywords(text, top_k=10):
    """
    Use an LLM to suggest the top domain-specific keywords from the text.
    """

    system_prompt = "You are an SEO keyword export who is a master at coming up with the exact keywords that a website wants to rank for in order to increase it's ranking in traditional sources like Google search but also new sources like ChatGPT, Perplexity and Claude."

    prompt = f"""
    Below is text from a website. Please extract the {top_k} most relevant 
    keywords or short phrases that represent the main topics of the site. 
    Return them as a comma-separated list with no extra commentary.

    Text:
    {text['markdown']}
    """

    content = call_openai(system_prompt, prompt)
    
    # Expect a comma-separated list, parse it
    keywords = [kw.strip() for kw in content.split(",")]

    print(keywords[:top_k])
    
    # In case the model returns fewer or more than top_k, prune or handle accordingly
    return keywords[:top_k]

def generate_prompts_llm(keywords, domain_description, prompts_per_keyword=5):
    """
    - keywords: list of strings
    - domain_description: short text describing the product or service
    - prompts_per_keyword: how many distinct queries to generate per keyword
    """

    system_prompt = "You are an LLM search  export who is a master at coming up with the exact phrases that a real user would use to search for different software tools in ChatGPT, Perplexity and Claude."

    all_prompts = []
    for kw in keywords:
        prompt = f"""
        This is the markdown text from the website: {domain_description}. 
        The keyword is: {kw}.

        Please generate {prompts_per_keyword} distinct user-like queries 
        that someone might type into an LLM-based search tool (like ChatGPT) 
        if they want to find a product or solution related to '{kw}'. 
        Make them natural-sounding and relevant to discovering new tools or advice.

        Return them as a numbered list only, with no extra commentary.
        """


        content = call_openai(system_prompt, prompt)

        print("the content", content)

        # Parse line by line
        lines = content.strip().split('\n')
        # Filter out lines that contain the queries
        for line in lines:
            line = line.strip()
            # Very rough parse: if it starts with a digit and a period
            if line and (line[0].isdigit() or line.startswith('-')):
                # Strip leading numbers / punctuation
                prompt_text = line.lstrip('0123456789.-) ').strip()
                all_prompts.append(prompt_text)

    return all_prompts

async def run_llm_queries(prompts, domain, brand_name="Neosync"):
    """
    Run search queries across multiple LLMs and track domain rankings.
    
    Args:
        prompts: List of search prompts to test
        domain: Domain to track rankings for (e.g., "neosync.dev")
        brand_name: Brand name to also look for in responses
        
    Returns:
        Dictionary with rankings by LLM and prompt
    """
    # Clean domain for comparison
    clean_domain = domain.replace("https://", "").replace("http://", "").replace("www.", "")
    
    # Define system prompt for all LLMs
    system_prompt = """
    You are a helpful assistant that recommends software tools and solutions.
    When asked about tools in a certain category, provide a clear numbered list of the top options.
    For each tool, include:
    1. The name of the tool
    2. A brief description (1-2 sentences)
    3. The website URL if you know it
    
    Format your response as a numbered list with 5-10 items. Do not include any disclaimers or additional commentary.
    """
    
    # Dictionary to store results
    results = {}
    
    # Define which LLMs to use with their respective calling functions and parsers
    llms = {
        "openai": {
            "caller": call_openai,
            "parser": parse_openai_response
        },
        # "claude": {
        #     "caller": call_claude,
        #     "parser": parse_claude_response
        # },
        # "perplexity": {
        #     "caller": call_perplexity,
        #     "parser": parse_perplexity_response
        # }
    }
    
    # Process each LLM
    for llm_name, llm_config in llms.items():
        print(f"\nProcessing {llm_name} queries...")
        results[llm_name] = {}
        
        caller_func = llm_config["caller"]
        parser_func = llm_config["parser"]
        
        for prompt in tqdm(prompts, desc=f"{llm_name} queries"):
            try:
                # 1. Call the LLM
                raw_response = caller_func(system_prompt, prompt)
                
                # Save the raw response for reference
                raw_response_preview = (raw_response[:500] + "..." 
                                      if len(raw_response) > 500 else raw_response)
                
                # 2. Parse the response to get structured tool data
                try:
                    parsed_tools = parser_func(raw_response)
                except Exception as e:
                    print(f"Error parsing {llm_name} response for prompt '{prompt[:30]}...': {str(e)}")
                    traceback.print_exc()
                    parsed_tools = []
                
                # 3. Find where our domain/brand ranks in the parsed tools
                if parsed_tools:
                    rank = find_rank_in_tools(clean_domain, brand_name, parsed_tools)
                else:
                    # If parsing failed but we have a response, fall back to text search
                    if "Error:" not in raw_response:
                        # Simple text-based mention check
                        if clean_domain in raw_response.lower() or brand_name.lower() in raw_response.lower():
                            rank = "Mentioned (parsing failed)"
                        else:
                            rank = "Not mentioned (parsing failed)"
                    else:
                        rank = "Error"
                
                # Store results
                results[llm_name][prompt] = {
                    "rank": rank,
                    "response": raw_response_preview,
                    "parsed_tools_count": len(parsed_tools)
                }
                
                # Add parsed tools for reference (limit to 3 for brevity)
                if parsed_tools:
                    results[llm_name][prompt]["sample_tools"] = parsed_tools[:3]
                
            except Exception as e:
                print(f"Unexpected error processing {prompt} with {llm_name}: {str(e)}")
                traceback.print_exc()
                results[llm_name][prompt] = {
                    "rank": "Error",
                    "response": f"Error: {str(e)}",
                    "parsed_tools_count": 0
                }
            
            # Add a small delay to avoid rate limits
            await asyncio.sleep(0.5)
    
    return results



# def find_rank_in_response(domain, brand, response_text):
#     """
#     Attempt to parse enumerated or bulleted lists for a mention of domain or brand.
#     If found, try to determine rank (1st, 2nd, etc.).
#     If not enumerated, look for any mention in paragraphs.
#     Return either the rank (int) or 'Mentioned (unranked)' or 'Not mentioned'.
#     """
#     # Combine domain + brand name for searching
#     search_terms = [domain.lower(), brand.lower()]
    
#     # Split by line
#     lines = response_text.split('\n')
#     rank = None

#     # We'll keep track of enumerated item counters
#     enumerated_counter = 0
    
#     for line in lines:
#         line_clean = line.strip()
#         # Basic enumerated pattern: "1.", "2)", "- ", "* ", "• " etc.
#         enum_match = re.match(r"^(\d+)[\.\)]\s+|^[\-\*\•]\s+", line_clean)
        
#         if enum_match:
#             enumerated_counter += 1  # we found a new enumerated bullet

#             # Now check if brand or domain is in this line
#             if any(term in line_clean.lower() for term in search_terms):
#                 # If found, the enumerated_counter is effectively the rank
#                 rank = enumerated_counter
#                 break
#         else:
#             # It's a line not obviously enumerated. We can do a simpler check
#             # for brand mention.
#             if any(term in line_clean.lower() for term in search_terms):
#                 # We'll keep track that it's 'mentioned' but not enumerated
#                 rank = "Mentioned (unranked)"
#                 # Keep scanning in case we find an enumerated mention further down
    
#     if not rank:
#         rank = "Not mentioned"

#     return rank

async def main(domain, max_pages=10, output_file="llm_ranking_report.pdf"):
    """Main function to run the entire workflow."""
    # Extract domain name for brand searching
    brand_name = domain.replace("https://", "").replace("http://", "").replace("www.", "").split('.')[0]
    brand_name = brand_name.capitalize()
    
    # 1. Scrape website content or use provided content
    print("\n--- Step 1: Getting Website Content ---")
    try:
        # Use md_text if it's already imported and available
        if 'md_text' in globals() and isinstance(md_text, dict) and 'markdown' in md_text:
            website_content = md_text
            print("Using pre-loaded website content")
        else:
            website_content = scrape_website(domain, max_pages)
        
        if not website_content or not website_content.get('markdown'):
            print("Failed to get website content. Using example data.")
            website_content = {'markdown': 'Example website content'}
    except Exception as e:
        print(f"Error getting website content: {str(e)}")
        website_content = {'markdown': 'Example website content'}
    
    # 2. Extract keywords from content
    print("\n--- Step 2: Extracting Keywords ---")
    keywords = extract_keywords(website_content, top_k=10)
    
    # 3. Generate search prompts from keywords
    print("\n--- Step 3: Generating Search Prompts ---")
    prompts = generate_prompts_llm(keywords, website_content, prompts_per_keyword=3)
    
    # 4. Run search queries across multiple LLMs
    print("\n--- Step 4: Running LLM Queries ---")
    llm_results = await run_llm_queries(prompts, domain, brand_name)
    
    # 5. Generate PDF report
    print("\n--- Step 5: Generating PDF Report ---")
    try:
        report_file = generate_pdf_report(llm_results, domain, keywords, output_file)
        print(f"\nAnalysis complete! Report saved to: {report_file}")
    except Exception as e:
        print(f"Error generating PDF report: {str(e)}")
        traceback.print_exc()
        print("\nAnalysis completed, but PDF generation failed.")
    
    return {
        "domain": domain,
        "keywords": keywords,
        "prompts": prompts,
        "results": llm_results,
        "output_file": output_file
    }


if __name__ == "__main__":
    import sys
    
    # Get domain from command line argument or use default
    domain = sys.argv[1] if len(sys.argv) > 1 else "https://www.neosync.dev"
    
    print(f"Starting LLM ranking analysis for: {domain}")
    print("=" * 50)
    
    # Run the main async function
    asyncio.run(main(domain))