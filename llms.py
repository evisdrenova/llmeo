from openai import OpenAI
from dotenv import load_dotenv
import anthropic
import os
from typing import List, Dict, Any, Union
import re
import json
import traceback

load_dotenv()


oai_api_key = os.getenv("OPENAI_API")
oai_client = OpenAI(api_key=oai_api_key)

pplx_api_key = os.getenv("PPLX_API")
pplx_client = OpenAI(api_key=pplx_api_key, base_url="https://api.perplexity.ai")

claude_api_key = os.getenv("ANTHROPIC_API")
anthropic_client = anthropic.Anthropic(api_key=claude_api_key)


def call_perplexity(system_prompt, prompt, model="sonar-pro"):
        """
       wrapper function around the perplexity api to call the perplexity api
       defaults to gpt-4o
       """
        
        messages = [
        {
        "role": "system",
        "content": system_prompt
        },
        {   
        "role": "user",
        "content": prompt
            },
        ]

        response = pplx_client.chat.completions.create(
            model=model,
            messages=messages,
        )

        return response


def call_perplexity(system_prompt, prompt, model="sonar-medium-online"):
    """Call Perplexity API with system and user prompts."""
    try:
        messages = [
            {
            "role": "system",
            "content": system_prompt
            },
            {   
            "role": "user",
            "content": prompt
                },
            ]

        
        response = pplx_client.chat.completions.create(
                model=model,
                messages=messages,
            )

        
        if response.status_code == 200:
            result = response.model_dump_json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
        
        return f"Error: Perplexity API returned status {response.status_code}"
    except Exception as e:
        print(f"Perplexity API error: {str(e)}")
        return f"Error: {str(e)}"


def call_openai(system_prompt, prompt, model="gpt-4o"):
    """Call OpenAI API with system and user prompts."""
    try:
        response = oai_client.responses.create(
            model=model,
            instructions=system_prompt,
            input=prompt,
            )
        return response.output[0].content[0].text
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        return f"Error: {str(e)}"


def call_claude(system_prompt, prompt, model="claude-3-haiku-20240307"):
    """Call Anthropic Claude API with system and user prompts."""
    try:
        message = anthropic_client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Handle Claude's response format
        if hasattr(message, 'content') and isinstance(message.content, list):
            # Extract text from all content blocks
            full_text = ""
            for content_block in message.content:
                if hasattr(content_block, 'text'):
                    full_text += content_block.text
                elif isinstance(content_block, dict) and 'text' in content_block:
                    full_text += content_block['text']
            
            return full_text
        else:
            # Fallback for unexpected response format
            return str(message)
            
    except Exception as e:
        print(f"Claude API error: {str(e)}")
        return f"Error: {str(e)}"



def parse_openai_response(response_text: str) -> List[Dict[str, str]]:
    """
    Parse OpenAI's response into a list of tools.
    
    Args:
        response_text: Raw text response from OpenAI
        
    Returns:
        List of dictionaries, each with 'name', 'description', and 'url' keys
    """
    tools = []
    lines = response_text.split('\n')
    
    current_tool = {}
    tool_pattern = re.compile(r'^(\d+)\.\s+(.+)$')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a new tool entry
        match = tool_pattern.match(line)
        if match:
            # If we were building a previous tool, add it to our list
            if current_tool and 'name' in current_tool:
                tools.append(current_tool)
                
            # Start a new tool
            tool_name = match.group(2)
            # Extract URL if it's in the same line
            url_match = re.search(r'(https?://[^\s]+)', tool_name)
            
            if url_match:
                url = url_match.group(1)
                tool_name = tool_name.replace(url, '').strip()
                current_tool = {'name': tool_name, 'url': url, 'description': ''}
            else:
                current_tool = {'name': tool_name, 'url': '', 'description': ''}
        
        elif current_tool and 'name' in current_tool:
            # This line is part of the current tool's description or URL
            url_match = re.search(r'(https?://[^\s]+)', line)
            if url_match and not current_tool['url']:
                current_tool['url'] = url_match.group(1)
                line = line.replace(url_match.group(1), '').strip()
                
            if line and not url_match:
                if current_tool['description']:
                    current_tool['description'] += ' ' + line
                else:
                    current_tool['description'] = line
    
    # Don't forget the last tool
    if current_tool and 'name' in current_tool:
        tools.append(current_tool)
        
    return tools


def parse_claude_response(response_text: str) -> List[Dict[str, str]]:
    """
    Parse Claude's response into a list of tools.
    
    Args:
        response_text: Raw text response from Claude
        
    Returns:
        List of dictionaries, each with 'name', 'description', and 'url' keys
    """
    tools = []
    lines = response_text.split('\n')
    
    current_tool = {}
    # Claude tends to use numbered lists with periods or parentheses
    tool_pattern = re.compile(r'^(\d+)[\.\)]\s+(.+)$')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a new tool entry
        match = tool_pattern.match(line)
        if match:
            # If we were building a previous tool, add it to our list
            if current_tool and 'name' in current_tool:
                tools.append(current_tool)
                
            # Start a new tool
            tool_text = match.group(2)
            
            # Claude often puts the URL at the end of the line
            url_match = re.search(r'(https?://[^\s]+)$', tool_text)
            
            if url_match:
                url = url_match.group(1)
                tool_name = tool_text[:tool_text.rfind(url)].strip()
                current_tool = {'name': tool_name, 'url': url, 'description': ''}
            else:
                # Try to find the tool name (often before the first period or dash)
                name_end_match = re.search(r'^([^\.|\-]+)', tool_text)
                if name_end_match:
                    tool_name = name_end_match.group(1).strip()
                    description = tool_text[len(tool_name):].strip()
                    # Remove leading punctuation from description
                    description = re.sub(r'^[\s\-:]+', '', description)
                    current_tool = {'name': tool_name, 'url': '', 'description': description}
                else:
                    current_tool = {'name': tool_text, 'url': '', 'description': ''}
        
        elif current_tool and 'name' in current_tool:
            # This line is part of the current tool's description or URL
            url_match = re.search(r'(https?://[^\s]+)', line)
            if url_match and not current_tool['url']:
                current_tool['url'] = url_match.group(1)
                line = line.replace(url_match.group(1), '').strip()
                
            if line and not url_match:
                if current_tool['description']:
                    current_tool['description'] += ' ' + line
                else:
                    current_tool['description'] = line
    
    # Don't forget the last tool
    if current_tool and 'name' in current_tool:
        tools.append(current_tool)
        
    return tools


def parse_perplexity_response(response_text: str) -> List[Dict[str, str]]:
    """
    Parse Perplexity's response into a list of tools.
    
    Args:
        response_text: Raw text response from Perplexity
        
    Returns:
        List of dictionaries, each with 'name', 'description', and 'url' keys
    """
    tools = []
    lines = response_text.split('\n')
    
    current_tool = {}
    # Perplexity often uses numbered lists with periods, or bullet points
    tool_pattern = re.compile(r'^(\d+)[\.\)]\s+(.+)$|^[\*\-\•]\s+(.+)$')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a new tool entry
        match = tool_pattern.match(line)
        if match:
            # If we were building a previous tool, add it to our list
            if current_tool and 'name' in current_tool:
                tools.append(current_tool)
                
            # Start a new tool - handle both numbered and bulleted formats
            tool_text = match.group(2) if match.group(2) else match.group(3)
            
            # Extract URL if present
            url_match = re.search(r'(https?://[^\s]+)', tool_text)
            if url_match:
                url = url_match.group(1)
                # Remove URL from the tool text for further processing
                clean_text = tool_text.replace(url, '').strip()
                
                # Perplexity often formats as "Tool Name - Description"
                parts = re.split(r'\s+[\-\:]\s+', clean_text, 1)
                if len(parts) > 1:
                    tool_name = parts[0]
                    description = parts[1]
                else:
                    tool_name = clean_text
                    description = ""
                    
                current_tool = {'name': tool_name, 'url': url, 'description': description}
            else:
                # No URL, try to split name and description
                parts = re.split(r'\s+[\-\:]\s+', tool_text, 1)
                if len(parts) > 1:
                    tool_name = parts[0]
                    description = parts[1]
                else:
                    tool_name = tool_text
                    description = ""
                    
                current_tool = {'name': tool_name, 'url': '', 'description': description}
        
        elif current_tool and 'name' in current_tool:
            # This line is part of the current tool's description or URL
            url_match = re.search(r'(https?://[^\s]+)', line)
            if url_match and not current_tool['url']:
                current_tool['url'] = url_match.group(1)
                line = line.replace(url_match.group(1), '').strip()
                
            if line and not url_match:
                if current_tool['description']:
                    current_tool['description'] += ' ' + line
                else:
                    current_tool['description'] = line
    
    # Don't forget the last tool
    if current_tool and 'name' in current_tool:
        tools.append(current_tool)
        
    return tools



def find_rank_in_tools(domain: str, brand: str, tools: List[Dict[str, str]]) -> Union[int, str]:
    """
    Find the ranking of a domain/brand in a list of parsed tools.
    
    Args:
        domain: Domain to search for (e.g., "neosync.dev")
        brand: Brand name to search for (e.g., "Neosync")
        tools: List of tool dictionaries with 'name', 'description', and 'url' keys
        
    Returns:
        int: Position in the list (1-based) if found
        str: "Mentioned (unranked)" if mentioned but not as a primary tool
        str: "Not mentioned" if not found at all
    """
    # Clean domain and brand for comparison
    domain_clean = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    brand_clean = brand.lower()
    
    # First check if any tools directly mention our domain/brand
    for i, tool in enumerate(tools):
        tool_name = tool.get('name', '').lower()
        tool_url = tool.get('url', '').lower()
        tool_desc = tool.get('description', '').lower()
        
        # Check name and URL first (these are more important matches)
        if (domain_clean in tool_url or 
            brand_clean in tool_name or 
            domain_clean in tool_name):
            return i + 1  # Return 1-based position
            
    # If not found as a primary mention, check for secondary mentions in descriptions
    for tool in tools:
        tool_desc = tool.get('description', '').lower()
        if domain_clean in tool_desc or brand_clean in tool_desc:
            return "Mentioned (unranked)"
    
    # If we get here, the domain/brand was not mentioned
    return "Not mentioned"