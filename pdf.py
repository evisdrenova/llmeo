from fpdf import FPDF
import matplotlib.pyplot as plt
import os
import numpy as np
from datetime import datetime

class PDF(FPDF):
    def header(self):
        # Logo (you can replace with your company logo)
        # self.image('logo.png', 10, 8, 33)
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(80)
        # Title
        self.cell(30, 10, 'LLM Ranking Report', 0, 0, 'C')
        # Line break
        self.ln(20)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')
        # Date
        self.cell(-40, 10, datetime.now().strftime("%Y-%m-%d"), 0, 0, 'R')

def generate_pdf_report(rankings, domain, keywords, output_file="llm_ranking_report.pdf"):
    """
    Generate a very simple PDF report that avoids encoding issues.
    
    Args:
        rankings: Dictionary with ranking results by LLM and prompt
        domain: The domain that was analyzed
        keywords: List of keywords that were extracted
        output_file: Output PDF filename
    """
    pdf = FPDF()
    pdf.add_page()

    clean_domain = domain.replace("https://", "").replace("http://", "")
    
    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "LLM Ranking Report for {clean_domain}", ln=True, align='C')
    
    # Domain
    pdf.set_font("Arial", "B", 14)
    clean_domain = domain.replace("https://", "").replace("http://", "")
    pdf.cell(0, 10, f"Domain: {clean_domain}", ln=True)
    
    # Date
    pdf.set_font("Arial", "", 10)
    from datetime import datetime
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    
    # Keywords
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Keywords:", ln=True)
    pdf.set_font("Arial", "", 10)
    
    # Join keywords with commas to avoid encoding issues
    keywords_text = ", ".join([k for k in keywords if isinstance(k, str)][:10])
    pdf.multi_cell(0, 5, keywords_text)
    pdf.ln(5)
    
    # Summary for each LLM
    for llm_name, prompts_data in rankings.items():
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Results for {llm_name.upper()}", ln=True)
        
        # Count stats
        total_queries = len(prompts_data)
        mentioned = 0
        top_ranked = 0
        
        for data in prompts_data.values():
            rank = data.get("rank", "Error")
            if rank != "Not mentioned" and "Error" not in str(rank):
                mentioned += 1
            if isinstance(rank, int) and rank <= 3:
                top_ranked += 1
        
        # Show stats
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 8, f"Total Queries: {total_queries}", ln=True)
        pdf.cell(0, 8, f"Times Mentioned: {mentioned}", ln=True)
        pdf.cell(0, 8, f"Top 3 Rankings: {top_ranked}", ln=True)
        
        mention_rate = (mentioned / total_queries * 100) if total_queries > 0 else 0
        top_rate = (top_ranked / total_queries * 100) if total_queries > 0 else 0
        
        pdf.cell(0, 8, f"Mention Rate: {mention_rate:.1f}%", ln=True)
        pdf.cell(0, 8, f"Top 3 Rate: {top_rate:.1f}%", ln=True)
        pdf.ln(5)
        
        # List individual query results
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Query Results:", ln=True)
        
        for prompt, data in prompts_data.items():
            # Simplify the prompt to prevent encoding issues
            safe_prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
            safe_prompt = "".join(c for c in safe_prompt if c.isalnum() or c in " .,?!-")
            
            rank = data.get("rank", "Error")
            rank_display = f"#{rank}" if isinstance(rank, int) else str(rank)
            
            pdf.set_font("Arial", "B", 10)
            pdf.multi_cell(0, 6, f"Query: {safe_prompt}")
            
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"Rank: {rank_display}", ln=True)
            pdf.ln(3)
    
    # Overall conclusion
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Overall Performance", ln=True)
    
    # Calculate overall performance
    total_overall = 0
    mentioned_overall = 0
    top_ranked_overall = 0
    
    for llm_name, prompts_data in rankings.items():
        total_overall += len(prompts_data)
        
        for data in prompts_data.values():
            rank = data.get("rank", "Error")
            if rank != "Not mentioned" and "Error" not in str(rank):
                mentioned_overall += 1
            if isinstance(rank, int) and rank <= 3:
                top_ranked_overall += 1
    
    overall_mention_rate = (mentioned_overall / total_overall * 100) if total_overall > 0 else 0
    overall_top_rate = (top_ranked_overall / total_overall * 100) if total_overall > 0 else 0
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Total Queries: {total_overall}", ln=True)
    pdf.cell(0, 8, f"Overall Mention Rate: {overall_mention_rate:.1f}%", ln=True)
    pdf.cell(0, 8, f"Overall Top 3 Rate: {overall_top_rate:.1f}%", ln=True)
    
    # Save the report
    try:
        pdf.output(output_file)
        return output_file
    except Exception as e:
        # If we still have issues, try a different filename
        alt_output = "simple_report.pdf"
        try:
            pdf.output(alt_output)
            return alt_output
        except Exception as e2:
            print(f"Failed to generate PDF: {str(e2)}")
            return None

def summarize_rankings(rankings):
    """Generate summary statistics from rankings data."""
    summary = {
        "total_queries": 0,
        "mentions_by_llm": {},
        "top_rankings": {},
        "not_mentioned": {}
    }
    
    for llm_name, prompts_data in rankings.items():
        # Initialize counters for this LLM
        total_queries = len(prompts_data)
        mentioned_count = 0
        top_rankings = 0
        not_mentioned = 0
        
        # Process each prompt
        for prompt, data in prompts_data.items():
            rank = data["rank"]
            
            if isinstance(rank, int):
                mentioned_count += 1
                if rank <= 3:  # Considered a top ranking (position 1-3)
                    top_rankings += 1
            elif rank == "Mentioned (unranked)":
                mentioned_count += 1
            elif rank == "Not mentioned":
                not_mentioned += 1
        
        # Store in summary
        summary["total_queries"] += total_queries
        summary["mentions_by_llm"][llm_name] = {
            "total": total_queries,
            "mentioned": mentioned_count,
            "top_ranked": top_rankings,
            "not_mentioned": not_mentioned,
            "mention_rate": round(mentioned_count / total_queries * 100, 1) if total_queries > 0 else 0,
            "top_rate": round(top_rankings / total_queries * 100, 1) if total_queries > 0 else 0
        }
    
    return summary

def generate_charts(summary_data, domain, filename="temp_chart.png"):
    """Generate visualization charts for the report."""
    # Set style
    plt.style.use('ggplot')
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Prepare data
    llm_names = list(summary_data["mentions_by_llm"].keys())
    mention_rates = [summary_data["mentions_by_llm"][llm]["mention_rate"] for llm in llm_names]
    top_rates = [summary_data["mentions_by_llm"][llm]["top_rate"] for llm in llm_names]
    
    # Plot 1: Mention Rates
    ax1.bar(llm_names, mention_rates, color='skyblue')
    ax1.set_title(f'Mention Rate by LLM for {domain}')
    ax1.set_ylabel('Percentage of Queries (%)')
    ax1.set_ylim(0, 100)
    
    # Add value labels
    for i, v in enumerate(mention_rates):
        ax1.text(i, v + 2, f"{v}%", ha='center')
    
    # Plot 2: Top Rankings
    ax2.bar(llm_names, top_rates, color='lightgreen')
    ax2.set_title(f'Top-3 Ranking Rate by LLM')
    ax2.set_ylabel('Percentage of Queries (%)')
    ax2.set_ylim(0, 100)
    
    # Add value labels
    for i, v in enumerate(top_rates):
        ax2.text(i, v + 2, f"{v}%", ha='center')
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    return filename

def generate_summary_text(summary_data, domain):
    """Generate executive summary text based on the data."""
    llm_names = list(summary_data["mentions_by_llm"].keys())
    
    # Find best and worst performing LLMs
    mention_rates = [summary_data["mentions_by_llm"][llm]["mention_rate"] for llm in llm_names]
    top_rates = [summary_data["mentions_by_llm"][llm]["top_rate"] for llm in llm_names]
    
    best_mention_llm = llm_names[np.argmax(mention_rates)]
    worst_mention_llm = llm_names[np.argmin(mention_rates)]
    best_top_llm = llm_names[np.argmax(top_rates)]
    
    # Generate summary
    text = f"""This report analyzes how {domain} performs in search results across different LLMs.

Key Findings:
• A total of {summary_data["total_queries"]} search queries were tested across {len(llm_names)} different LLMs.
• {domain} performed best in {best_mention_llm.upper()}, appearing in {summary_data["mentions_by_llm"][best_mention_llm]["mention_rate"]}% of search results.
• {domain} was least visible in {worst_mention_llm.upper()}, appearing in only {summary_data["mentions_by_llm"][worst_mention_llm]["mention_rate"]}% of results.
• {domain} achieved top-3 placement most often in {best_top_llm.upper()} ({summary_data["mentions_by_llm"][best_top_llm]["top_rate"]}% of queries).

Recommendations:
• Focus SEO optimization efforts on improving visibility in {worst_mention_llm.upper()}.
• Leverage successful visibility patterns from {best_mention_llm.upper()} across all platforms.
• Monitor competitors' performance and optimize content to maintain top rankings.
"""
    return text





def create_simple_report(rankings, domain, keywords, output_file="simple_report.pdf"):
    """Create a simplified PDF report that avoids Unicode issues"""
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"LLM Ranking Report", ln=True, align='C')
    pdf.ln(5)
    
    # Domain
    pdf.set_font("Arial", "B", 14)
    clean_domain = domain.replace("https://", "").replace("http://", "")
    pdf.cell(0, 10, f"Domain: {clean_domain}", ln=True)
    
    # Keywords
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Keywords:", ln=True)
    pdf.set_font("Arial", "", 10)
    
    keywords_text = ", ".join(keywords[:10])
    pdf.multi_cell(0, 5, keywords_text)
    pdf.ln(5)
    
    # Results summary
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Results Summary:", ln=True)
    
    for llm_name, prompts_data in rankings.items():
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, f"{llm_name.upper()}", ln=True)
        
        # Count mentions
        total_queries = len(prompts_data)
        mentioned = sum(1 for data in prompts_data.values() if data["rank"] != "Not mentioned" and "Error" not in data["rank"])
        top_ranked = sum(1 for data in prompts_data.values() if isinstance(data["rank"], int) and data["rank"] <= 3)
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Total Queries: {total_queries}", ln=True)
        pdf.cell(0, 6, f"Mentioned: {mentioned} ({int(mentioned/total_queries*100)}%)", ln=True)
        pdf.cell(0, 6, f"Top 3 Rankings: {top_ranked} ({int(top_ranked/total_queries*100)}%)", ln=True)
        pdf.ln(5)
    
    # Save the simplified report
    output_file = "simple_" + output_file
    pdf.output(output_file)
    return output_file