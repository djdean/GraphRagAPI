import getpass
import json
import time
from pathlib import Path

import magic
import requests
from devtools import pprint
from tqdm import tqdm

def main():
    endpoint = "https://apim-ztsvn4lql4hfq.azure-api.net"
    openai_key = "0c46a21bb1d14f309981a1dcab7b271e"
    openai_api_version = "2024-07-01-preview"
    model = "gpt-4o"
    model_family = "gpt-4"
    model_cost =  0.005

    ocp_apim_subscription_key = "59040eacfdcb4a7cb523547fbe2ab875"
    
    #getpass.getpass("516ac1ab72b141f4801078eaf46aa2f8")

    """
    "Ocp-Apim-Subscription-Key": 
        This is a custom HTTP header used by Azure API Management service (APIM) to 
        authenticate API requests. The value for this key should be set to the subscription 
        key provided by the Azure APIM instance in your GraphRAG resource group.
    """
    headers = {"Ocp-Apim-Subscription-Key": ocp_apim_subscription_key}
    """
    These parameters must be defined by the notebook user:

    - file_directory: a local directory of text files. The file structure should be flat,
                    with no nested directories. (i.e. file_directory/file1.txt, file_directory/file2.txt, etc.)
    - storage_name:   a unique name to identify a blob storage container in Azure where files
                    from `file_directory` will be uploaded.
    - index_name:     a unique name to identify a single graphrag knowledge graph index.
                    Note: Multiple indexes may be created from the same `storage_name` blob storage container.
    - endpoint:       the base/endpoint URL for the GraphRAG API (this is the Gateway URL found in the APIM resource).
    """

    file_directory = r"C:\Users\dade\Desktop\Pfizer RWE Code With Engagement\raginputdata"
    storage_name = "raginputdata"
    index_name = "graphragindex"
    endpoint = "https://apim-ztsvn4lql4hfq.azure-api.net"
    response = upload_files(
        file_directory=file_directory,
        storage_name=storage_name,
        batch_size=100,
        overwrite=True, # overwrite files if they already exist in the storage blob container
    )
    if not response.ok:
        print(response.text)
    else:
        print(response)
        
def upload_files(
    file_directory: str,
    storage_name: str,
    batch_size: int = 100,
    overwrite: bool = True,
    max_retries: int = 5,
) -> requests.Response | list[Path]:
    """
    Upload files to a blob storage container.

    Args:
    file_directory - a local directory of .txt files to upload. All files must have utf-8 encoding.
    storage_name - a unique name for the Azure storage blob container.
    batch_size - the number of files to upload in a single batch.
    overwrite - whether or not to overwrite files if they already exist in the storage blob container.
    max_retries - the maximum number of times to retry uploading a batch of files if the API is busy.

    NOTE: Uploading files may sometimes fail if the blob container was recently deleted
    (i.e. a few seconds before. The solution "in practice" is to sleep a few seconds and try again.
    """
    #ocp_apim_subscription_key = getpass.getpass("516ac1ab72b141f4801078eaf46aa2f8")
    ocp_apim_subscription_key = "72e2aba38d6f40eeb42f7a94d04197a7"
    """
    "Ocp-Apim-Subscription-Key": 
        This is a custom HTTP header used by Azure API Management service (APIM) to 
        authenticate API requests. The value for this key should be set to the subscription 
        key provided by the Azure APIM instance in your GraphRAG resource group.
    """
    headers = {"Ocp-Apim-Subscription-Key": ocp_apim_subscription_key}
    endpoint = "https://apim-3q5vgd3e7fyig.azure-api.net"
    url = endpoint + "/data"
    def upload_batch(
        files: list, storage_name: str, overwrite: bool, max_retries: int
    ) -> requests.Response:
        for _ in range(max_retries):
            response = requests.post(
                url=url,
                files=files,
                params={"storage_name": storage_name, "overwrite": overwrite},
                headers=headers,
            )
            # API may be busy, retry
            if response.status_code == 500:
                print("API busy. Sleeping and will try again.")
                time.sleep(10)
                continue
            return response
        return response
    batch_files = []
    accepted_file_types = ["text/plain"]
    filepaths = list(Path(file_directory).iterdir())
    for file in tqdm(filepaths):
        # validate that file is a file, has acceptable file type, has a .txt extension, and has utf-8 encoding
        if (
            not file.is_file()
            or file.suffix != ".txt"
            or magic.from_file(str(file), mime=True) not in accepted_file_types
        ):
            print(f"Skipping invalid file: {file}")
            continue
        # open and decode file as utf-8, ignore bad characters
        batch_files.append(
            ("files", open(file=file, mode="r", encoding="utf-8", errors="ignore"))
        )
        # upload batch of files
        if len(batch_files) == batch_size:
            response = upload_batch(batch_files, storage_name, overwrite, max_retries)
            # if response is not ok, return early
            if not response.ok:
                return response
            batch_files.clear()
    # upload remaining files
    if len(batch_files) > 0:
        response = upload_batch(batch_files, storage_name, overwrite, max_retries)
    return response

if __name__ == "__main__":
    main() 