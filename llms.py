from openai import OpenAI
from dotenv import load_dotenv
import anthropic
import os

load_dotenv()


oai_api_key = os.getenv("OPENAI_API")
oai_client = OpenAI(api_key=oai_api_key)

pplx_api_key = os.getenv("PPLX_API")
pplx_client = OpenAI(api_key=pplx_api_key, base_url="https://api.perplexity.ai")

claude_api_key = os.getenv("ANTHROPIC_API")
client = anthropic.Anthropic(api_key=claude_api_key)


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


def call_openai(system_prompt, prompt, model="gpt-4o"):
       """
       wrapper function around the openai api to call the OpenAI api
       defaults to gpt-4o
       """
       response = oai_client.responses.create(
            model=model,
            instructions=system_prompt,
            input=prompt,
        )
       
       return  response.output[0].content[0].text


def call_claude(system_prompt, prompt, model="claude-3-7-sonnet-20250219"):
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}]
    )
    print(message.content)
    return message.content