import requests
import click
import os
import time

def get_header(content_type='application/json'):
    api_key = 'sk-da4be4464b954d76b1b4371fe4cb6727' # this is a local thing anywya
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': content_type,
        'Accept': content_type
    }

def simple_api(url, method='GET', payload=None, content_type='application/json'):
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

@cli.command()
def list_knowledge():
    """List all available knowledge bases""" 

    knowledge_bases = [_ for _ in get_list_knowledge()]

    for knowledge_base_id, knowledge_base_name, knowledge_base_description, knowledge_base_files in knowledge_bases: 

        print(f"ID: {knowledge_base_id}, Name: {knowledge_base_name}, Description: {knowledge_base_description}")

        for file in knowledge_base_files:
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

def clean_filename(filename):
    """Remove extension from filename, strip whitespace, replace spaces with underscores, and remove directories"""
    name = os.path.basename(filename).rsplit('.', 1)[0]  # Get filename without path and extension
    return name.strip().replace(' ', '_')

@cli.command()
def list_discworld_pdfs():
    """List all PDF files in the Discworld collection"""
    pdf_path = '/opt/container/data/discworld pdfs'
    
    knowledge_bases = [_ for _ in get_list_knowledge()]
    try:
        # List all files in directory
        files = os.listdir(pdf_path)
        
        # Filter for PDFs and print them
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        print(f"Found {len(pdf_files)} PDF files")
        if pdf_files:
            for pdf in pdf_files:
                make_sure_book_exists(knowledge_bases, os.path.join(pdf_path, pdf))

        else:
            print("No PDF files found in the Discworld directory")
            
    except FileNotFoundError:
        print(f"Error: Directory not found: {pdf_path}")
    except Exception as e:
        print(f"Error accessing directory: {str(e)}")
        raise

def create_knowledge_base(name, description):
    url = 'http://open-webui:8080/api/v1/knowledge/'
    payload = {
        "name": name,
        "description": description
    }
    response = simple_api(url, method='POST', payload=payload)

    # Got a not permitted error, so I'm just going to do it manually
    # keeping this here for future reference
    raise Exception(response)

def add_file_to_openwebui(pdf, book_name):
    url = 'http://open-webui:8080/api/v1/files/'
    print(f"Uploading file {pdf} to {url}")
    
    headers = get_header('multipart/form-data')  # Change content type for file upload
    del headers['Content-Type']  # Let requests set the correct boundary
    
    files = {
        'file': (book_name, open(pdf, 'rb'), 'application/pdf')
    }
    
    response = requests.post(url, headers=headers, files=files)
    return response.json()

def add_to_knowledge_base(knowledge_base_id, file_id):
    url = f'http://open-webui:8080/api/v1/knowledge/{knowledge_base_id}/file/add'
    response = simple_api(url, method='POST', payload={'file_id': file_id})
    return response

def add_to_knowledge_base_loop(knowledge_base_id, file_id):
    response = add_to_knowledge_base(knowledge_base_id, file_id)
    if "Extracted content is not available for this file" in response["detail"]:
        wait_time = 5
        print(f"Extracted content is not available for this file, waiting {wait_time} seconds and trying again")
        time.sleep(wait_time)
        add_to_knowledge_base_loop(knowledge_base_id, file_id)
    else:
        return response

def make_sure_book_exists(knowledge_bases, pdf):
    book_name = clean_filename(pdf) 
    knowledge_base_exists = False
    for knowledge_base_id, knowledge_base_name, knowledge_base_description, knowledge_base_files in knowledge_bases:
        if "discworld_pdfs" in knowledge_base_name:
            knowledge_base_exists = True
            break
 
    if not knowledge_base_exists:
        print("Knowledge base does not exist, creating it")
        knowledge_base_id = create_knowledge_base("discworld_pdfs", "A knowledge base for the Discworld PDF collection")

    if len(knowledge_base_files) == 0:
        print("Knowledge base is empty, adding file")
        upload_response = add_file_to_openwebui(pdf, book_name)
        file_id = upload_response['id']
        file_name = upload_response['filename']
        print(f"Uploaded file {file_id}")
        
        add_to_knowledge_base_loop(knowledge_base_id, file_id)
    else:
        raise Exception(knowledge_base_files)




if __name__ == '__main__':
    cli()
