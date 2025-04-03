from llms import call_openai, call_perplexity, call_claude
from dotenv import load_dotenv
from mdtext import md_text
from fpdf import FPDF
import re
import asyncio
from tqdm import tqdm
from crawl import scrape_website

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
    
    # Define system prompt for all LLMs
    system_prompt = """
    You are a helpful assistant that recommends software tools and solutions.
    When asked about tools in a certain category, provide a clear numbered list of the top options.
    For each tool, include:
    1. The name of the tool
    2. A brief description (1-2 sentences)
    3. The website URL if you know it
    
    Format your response as a numbered list. Do not include any disclaimers or additional commentary.
    """
    
    # Dictionary to store results
    results = {}
    
    # Define which LLMs to use
    llms = {
        "openai": call_openai,
        "claude": call_claude,
        "perplexity": call_perplexity
    }
    
    # Process each prompt across all LLMs
    for llm_name, llm_func in llms.items():
        print(f"\nProcessing {llm_name} queries...")
        results[llm_name] = {}
        
        clean_domain = domain.replace("https://", "").replace("http://", "").replace("www.", "")
    

        for prompt in tqdm(prompts, desc=f"{llm_name} queries"):
            try:
                # Call the appropriate LLM function
                response = llm_func(system_prompt, prompt)
                
                # Find where our domain/brand ranks in the response
                rank = find_rank_in_response(clean_domain, brand_name, response)
                
                # Store results
                results[llm_name][prompt] = {
                    "rank": rank,
                    "response": response[:500] + "..." if len(response) > 500 else response  # Truncate for storage
                }
                
                # Add a small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error processing {prompt} with {llm_name}: {str(e)}")
                results[llm_name][prompt] = {
                    "rank": "Error",
                    "response": f"Error: {str(e)}"
                }
    
    return results

def find_rank_in_response(domain, brand, response_text):
    """
    Attempt to parse enumerated or bulleted lists for a mention of domain or brand.
    If found, try to determine rank (1st, 2nd, etc.).
    If not enumerated, look for any mention in paragraphs.
    Return either the rank (int) or 'Mentioned (unranked)' or 'Not mentioned'.
    """
    # Combine domain + brand name for searching
    search_terms = [domain.lower(), brand.lower()]
    
    # Split by line
    lines = response_text.split('\n')
    rank = None

    # We'll keep track of enumerated item counters
    enumerated_counter = 0
    
    for line in lines:
        line_clean = line.strip()
        # Basic enumerated pattern: "1.", "2)", "- ", "* ", "• " etc.
        enum_match = re.match(r"^(\d+)[\.\)]\s+|^[\-\*\•]\s+", line_clean)
        
        if enum_match:
            enumerated_counter += 1  # we found a new enumerated bullet

            # Now check if brand or domain is in this line
            if any(term in line_clean.lower() for term in search_terms):
                # If found, the enumerated_counter is effectively the rank
                rank = enumerated_counter
                break
        else:
            # It's a line not obviously enumerated. We can do a simpler check
            # for brand mention.
            if any(term in line_clean.lower() for term in search_terms):
                # We'll keep track that it's 'mentioned' but not enumerated
                rank = "Mentioned (unranked)"
                # Keep scanning in case we find an enumerated mention further down
    
    if not rank:
        rank = "Not mentioned"

    return rank


def generate_pdf_report(rankings, domain, output_file="report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"LLM Ranking Report for {domain}", ln=True)

    # Loop through LLM results
    for llm_name, prompts_data in rankings.items():
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Results for {llm_name}", ln=True)
        pdf.set_font("Arial", "", 12)
        # Print table of prompt -> rank
        for prompt, rank in prompts_data.items():
            pdf.multi_cell(0, 8, f"Prompt: {prompt}\nRank: {rank}\n", border=1, ln=1)
        pdf.ln(5)

    pdf.output(output_file)



async def main(domain, max_pages=10, output_file="llm_ranking_report.pdf"):
    """
    Main function to run the entire workflow.
    
    Args:
        domain: Website domain to analyze
        max_pages: Maximum pages to crawl
        output_file: Output PDF filename
    """
    # 1. Scrape website content
    md_text = scrape_website(domain, max_pages)
    
    # 2. Extract keywords from content
    keywords = extract_keywords(md_text, top_k=10)
    
    # 3. Generate search prompts from keywords
    prompts = generate_prompts_llm(keywords, md_text, prompts_per_keyword=3)
    
    # Extract domain name for brand searching
    brand_name = domain.replace("https://", "").replace("http://", "").replace("www.", "").split('.')[0]
    brand_name = brand_name.capitalize()  # Capitalize first letter
    
    # 4. Run search queries across multiple LLMs
    llm_results = await run_llm_queries(prompts, domain, brand_name)
    
    # 5. Generate PDF report
    report_file = generate_pdf_report(llm_results, domain, keywords, output_file)
    
    print(f"Analysis complete! Report saved to {report_file}")



if __name__ == "__main__":
    # text = scrape_website(domain)

    # kw = extract_keywords(md_text)

    # prompts = generate_prompts_llm(kw, md_text )

    # generate_pdf_report(domain_rankings, domain, output_file="llm_ranking_report.pdf")

    asyncio.run(main(domain))