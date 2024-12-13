import requests
build = False
def main():
    storage_name = "raginputdata"
    index_name = "graphrRAGindex"
    if build:
        response = build_index(storage_name=storage_name, index_name=index_name)
        print(response)
        if response.ok:
            print(response.text)
        else:
            print(f"Failed to submit job.\nStatus: {response.text}")
    else:
        response = index_status(index_name)
        print(response.json())

def index_status(index_name: str) -> requests.Response:
    ocp_apim_subscription_key = "59040eacfdcb4a7cb523547fbe2ab875"
    """
    "Ocp-Apim-Subscription-Key": 
        This is a custom HTTP header used by Azure API Management service (APIM) to 
        authenticate API requests. The value for this key should be set to the subscription 
        key provided by the Azure APIM instance in your GraphRAG resource group.
    """
    headers = {"Ocp-Apim-Subscription-Key": ocp_apim_subscription_key}
    endpoint = "https://apim-ztsvn4lql4hfq.azure-api.net"
    url = endpoint + f"/index/status/{index_name}"
    return requests.get(url, headers=headers)

    

def build_index(
    storage_name: str,
    index_name: str,
) -> requests.Response:
    """Create a search index.
    This function kicks off a job that builds a knowledge graph index from files located in a blob storage container.
    """
    ocp_apim_subscription_key = "59040eacfdcb4a7cb523547fbe2ab875"
    """
    "Ocp-Apim-Subscription-Key": 
        This is a custom HTTP header used by Azure API Management service (APIM) to 
        authenticate API requests. The value for this key should be set to the subscription 
        key provided by the Azure APIM instance in your GraphRAG resource group.
    """
    headers = {"Ocp-Apim-Subscription-Key": ocp_apim_subscription_key}
    endpoint = "https://apim-ztsvn4lql4hfq.azure-api.net"
    url = endpoint + "/index"
    request = {"storage_name": storage_name, "index_name": index_name}
    return requests.post(url, params=request, headers=headers)




if __name__ == "__main__":
    main()