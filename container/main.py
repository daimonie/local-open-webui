import requests
import click
import os
import time

class PromptException(Exception):
    pass

def get_header(content_type='application/json'):
    """Get HTTP headers for API requests.
    
    Args:
        content_type (str, optional): The content type for the request. Defaults to 'application/json'.
        
    Returns:
        dict: Dictionary containing Authorization, Content-Type and Accept headers
    """
    api_key = 'sk-da4be4464b954d76b1b4371fe4cb6727' # this is a local thing anywya

    os.environ['PARSE_CURL'] = "yes"

    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': content_type,
        'Accept': content_type
    }


def simple_api(url, method='GET', payload=None, content_type='application/json'):
    """Make a simple API request and optionally print the equivalent curl command.
    
    Args:
        url (str): The URL to make the request to
        method (str, optional): HTTP method to use. Defaults to 'GET'.
        payload (dict, optional): JSON payload for POST requests. Defaults to None.
        content_type (str, optional): Content type for the request. Defaults to 'application/json'.
        
    Returns:
        dict: JSON response from the API
    """
    headers = get_header(content_type)
    # Build header arguments for curl command
    header_args = ' '.join([f'-H "{k}: {v}"' for k, v in headers.items()])
    
    if method.upper() == 'GET':
        response = requests.get(url, headers=headers)
        curl_cmd = f"curl {header_args} {url}"
    else:
        response = requests.post(url, headers=headers, json=payload)
        curl_cmd = f"curl -X POST {header_args}"
        if payload is not None:
            curl_cmd += f" -d '{payload}'"
        curl_cmd += f" {url}"

    # print(curl_cmd)
    return response.json()
    

@click.group()
def cli():
    """CLI interface for interacting with local LLM models"""
    pass

@cli.command()
def list_models():
    """List all available models"""
    url = 'http://open-webui:8080/api/models'
    models = simple_api(url)

    for model in models['data']:
        model_id = model['id']
        name = model['name']

        if model_id == 'arena-model':
            continue # I don't know why this is in but go away
        print(f"ID: {model_id}, Name: {name}")

def get_list_knowledge():
    """List all available knowledge bases"""
    url = 'http://open-webui:8080/api/v1/knowledge/'
    knowledge_bases = simple_api(url)

    for kb in knowledge_bases:
        knowledge_base_id = kb['id']
        knowledge_base_name = kb['name']
        knowledge_base_description = kb['description']
        knowledge_base_files = kb['files']

        yield knowledge_base_id, knowledge_base_name, knowledge_base_description, knowledge_base_files

def list_knowledge_files(knowledge_base):

    """List all available files in knowledge base""" 

    knowledge_bases = [_ for _ in get_list_knowledge()]

    for knowledge_base_id, knowledge_base_name, knowledge_base_description, knowledge_base_files in knowledge_bases:  

        if knowledge_base in [knowledge_base_id, knowledge_base_name]:
                
            print(f"ID: {knowledge_base_id}, Name: {knowledge_base_name}, Description: {knowledge_base_description}")

            for file in knowledge_base_files:
                meta = file['meta']

                yield file["id"], meta['name'], meta['content_type']

@cli.command()
def list_knowledge():
    """List all available knowledge bases""" 

    knowledge_bases = [_ for _ in get_list_knowledge()]

    for knowledge_base_id, knowledge_base_name, knowledge_base_description, knowledge_base_files in knowledge_bases:  

        print(f"ID: {knowledge_base_id}, Name: {knowledge_base_name}, Description: {knowledge_base_description}")

        for file in knowledge_base_files:
            meta = file['meta']
            print(f"\tID: {file['id']}, Name: {meta['name']}, Content Type: {meta['content_type']}")

@cli.command()
def prompt_phi():
    """Send a prompt to the phi-3 model"""
    url = 'http://open-webui:8080/api/chat/completions'
    
    prompt = click.prompt('Enter your prompt', type=str)
    
    payload = {
        "model": "phi3:14b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 1.0
    }

    response = simple_api(url, method='POST', payload=payload)
    
    if 'choices' in response and len(response['choices']) > 0:
        print(response['choices'][0]['message']['content'])
    else:
        print("Error: Unexpected response format")
        print(response)

@cli.command()
def prompt_phi_knowledge():
    """Send a prompt to the phi-3 model""" 

    knowledge_base_id = "78d8f0c3-f35d-49be-826f-b65a94623bfa"
    
    url = 'http://open-webui:8080/api/chat/completions'
    
    prompt = click.prompt('Enter your prompt', type=str)
    
    payload = {
        "model": "phi3:14b",
        "messages": [{"role": "user", "content": prompt}],
        'files': [{'type': 'collection', 'id': knowledge_base_id}],
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 1.0
    }

    response = simple_api(url, method='POST', payload=payload)
    
    if 'choices' in response and len(response['choices']) > 0:
        print(response['choices'][0]['message']['content'])
    else:
        print("Error: Unexpected response format")
        print(response)

def clean_filename(filename):
    """Remove extension from filename, strip whitespace, replace spaces with underscores, and remove directories"""
    name = os.path.basename(filename).rsplit('.', 1)[0]  # Get filename without path and extension
    return name.strip().replace(' ', '_')

@cli.command()
def list_discworld_pdfs():
    """List all PDF files in the Discworld collection"""
    
    files = [_ for _ in list_knowledge_files("discworld_pdfs")]

    print("Listing knowledge base discworld_pdfs")
    for file_id, file_name, file_content_type in files:
        print(f"- {file_id} ({file_content_type}) {file_name}")

@cli.command()
def prompt_discworld_pdfs():
    """List all PDF files in the Discworld collection"""

    # First we need a question
    prompt = click.prompt('Enter your prompt', type=str)

    full_prompt = f"""
    You are a knowledgeable assistant capable of analyzing and identifying themes, quotes, and related sections in the Discworld series by Terry Pratchett.

    Your task is to determine whether a specific theme, quote, or concept appears in the book provided as context.
    Requirements:
    - Begin your response with "Yes," "Maybe," or "No" to indicate whether the quote or theme is present in the text.
    - Name the book provided in the context, "FILE_NAME". DO NOT refer to any other books.
    - The answer "Yes" is only allowed if this provided file is explicitly the source of the quote or theme.
    - If applicable, provide relevant excerpts or small paragraphs from the book that directly relate to the theme or quote, ensuring they capture its essence. Make sure to mark them as quotes.
    - If the quote or theme is not present, briefly explain why or suggest which other Discworld book(s) might contain it, if known.
    - Try to be concise in your response, but provide hte relevant excerpt or paragraph.
    - Your thematic or quote-specific query is: {prompt}
    """
    print(full_prompt)

    model = "mistral:latest"
    print(f"Using model: {model}")
    files = [_ for _ in list_knowledge_files("discworld_pdfs")]

    yes_responses = []
    maybe_responses = []
    no_responses = []


    with click.progressbar(files, label='Processing files', length=len(files)) as progress_files:
        for file_id, file_name, file_content_type in progress_files:

            response = api_prompt_discworld_pdfs(full_prompt.replace("FILE_NAME", file_name), file_id, model=model)
            
            try:
                first_word = response.split()[0].lower().strip().rstrip(',').strip()
            except Exception as e:
                first_word = "no"

            if first_word == "yes":
                yes_responses.append((file_name, response))
            elif first_word == "maybe":
                maybe_responses.append((file_name, response)) 
            elif first_word == "no":
                no_responses.append((file_name, response))
            else:
                print(f"Warning: Unexpected first word '{first_word}' in response from {file_name}")
                no_responses.append((file_name, response))
    
    if len(yes_responses) > 0:
        print("Yes responses:")
        for file_name, response in yes_responses:
            print(f"- {file_name}: {response}")
    elif len(maybe_responses) > 0:
        print("Maybe responses:")
        for file_name, response in maybe_responses:
            print(f"- {file_name}: {response}")
    else:
        print("Found no likely quotes.")
    

    final_responses = yes_responses
    if len(yes_responses) < 2:
        final_responses += yes_responses
    
    final_responses_item = ["From \"{file_name}\": {response}" for file_name, response in final_responses]

    final_prompt = f"""
        You are an editor tasked with combining multiple responses about a specific topic into a single, coherent, and polished text. Your goal is to merge the content logically, preserve the full context of any referenced quotes or sections, and ensure a well-structured narrative. Follow these steps:

        Introduction: Start with a concise introduction establishing the topic or query being addressed, based on the provided responses.
        Insert responseswhere relevant, ensuring they flow logically within the text. Remove redundancies between responses.
        If any response contains quotes or referenced sections, ensure they are introduced with context and retain their full length without alteration, even if they are lengthy. Do not paraphrase or shorten these sections.
        Conclusion: End with a brief summary or any additional clarifications to tie the information together.
        Tone and Style: Maintain a neutral tone, precise language, and logical flow throughout.
        Response Integration: Combine the key points from the responses:
        {"\n -".join(final_responses_item)}
    """

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": final_prompt}],
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 1.0
    }

    url = 'http://open-webui:8080/api/chat/completions'
    response = simple_api(url, method='POST', payload=payload)
    
    if 'choices' in response and len(response['choices']) > 0:
        print(response['choices'][0]['message']['content'])
    else:
        print("Error: Unexpected response format")
        print(response)

def api_prompt_discworld_pdfs(full_prompt, file_id, model="phi3:14b"):    
    url = 'http://open-webui:8080/api/chat/completions'
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": full_prompt}],
        'files': [{'type': 'file', 'id': file_id}],
        "temperature": 0.7,
        "max_tokens": 1000,
        "top_p": 1.0
    }

    response = simple_api(url, method='POST', payload=payload)
    
    if 'choices' in response and len(response['choices']) > 0:
        return response['choices'][0]['message']['content']
    else:
        raise PromptException("Did not get a recognised response from API")

if __name__ == '__main__':
    cli()
