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
    Generate a comprehensive PDF report of LLM rankings.
    
    Args:
        rankings: Dictionary with ranking results by LLM and prompt
        domain: The domain that was analyzed
        keywords: List of keywords that were extracted
        output_file: Output PDF filename
    """
    # Create summary data for visualization
    summary_data = summarize_rankings(rankings)
    
    # Generate visualizations
    chart_file = generate_charts(summary_data, domain)
    
    # Clean domain for display
    clean_domain = domain.replace("https://", "").replace("http://", "")
    
    # Create PDF
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"LLM Ranking Report for {clean_domain}", ln=True, align='C')
    pdf.ln(5)
    
    # Date and summary
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    
    # Executive Summary
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Executive Summary", ln=True)
    pdf.set_font("Arial", "", 10)
    
    # Add summary text
    summary_text = generate_summary_text(summary_data, clean_domain)
    pdf.multi_cell(0, 5, summary_text)
    pdf.ln(5)
    
    # Add visualization if available
    if os.path.exists(chart_file):
        pdf.image(chart_file, x=10, y=None, w=180)
        pdf.ln(5)
    
    # Keywords Section
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Top Keywords", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 5, "The following keywords were extracted from the domain and used to generate search queries:")
    
    for i, keyword in enumerate(keywords, 1):
        pdf.cell(0, 8, f"{i}. {keyword}", ln=True)
    pdf.ln(5)
    
    # Detailed Results by LLM
    for llm_name, prompts_data in rankings.items():
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Detailed Results: {llm_name.upper()}", ln=True)
        pdf.set_font("Arial", "", 10)
        
        for prompt, data in prompts_data.items():
            rank = data["rank"]
            rank_display = f"#{rank}" if isinstance(rank, int) else rank
            
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, f"Query: \"{prompt}\"", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 8, f"Rank: {rank_display}", ln=True)
            
            # Add response excerpt
            pdf.set_font("Arial", "I", 9)
            pdf.multi_cell(0, 5, f"Response excerpt: {data['response'][:300]}...")
            pdf.ln(5)
    
    # Clean up and save
    pdf.output(output_file)
    if os.path.exists(chart_file):
        os.remove(chart_file)  # Remove temporary chart file
    
    return output_file

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