import requests
import click

def get_header():
    api_key = 'sk-da4be4464b954d76b1b4371fe4cb6727' # this is a local thing anywya
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

def simple_api(url, method='GET', payload=None):
    headers = get_header()
    
    if method.upper() == 'GET':
        response = requests.get(url, headers=headers)
        curl_cmd = f"curl -H \"Authorization: {headers['Authorization']}\" {url}"
    else:
        response = requests.post(url, headers=headers, json=payload)
        curl_cmd = f"curl -X POST -H \"Authorization: {headers['Authorization']}\" -H \"Content-Type: application/json\" -d '{payload}' {url}"

    print(curl_cmd)
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

@cli.command()
def list_knowledge():
    """List all available knowledge bases"""
    url = 'http://open-webui:8080/api/v1/knowledge/'
    knowledge_bases = simple_api(url)


    for kb in knowledge_bases:
        knowledge_base_id = kb['id']
        knowledge_base_name = kb['name']
        knowledge_base_description = kb['description']

        print(f"ID: {knowledge_base_id}, Name: {knowledge_base_name}, Description: {knowledge_base_description}")

        for file in kb['files']:
            meta = file['meta']
            print(f"\tName: {meta['name']}, Content Type: {meta['content_type']}")

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


if __name__ == '__main__':
    cli()
