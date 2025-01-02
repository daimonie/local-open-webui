
import os
import requests


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