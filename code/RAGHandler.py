import requests
import json
from pathlib import Path
import time
from tqdm import tqdm

class RAGHandler:
    def __init__(self, key: str, 
                 endpoint: str, storage_name: str, 
                 index_name: str | list[str]):
        self.key = key
        self.endpoint = endpoint
        self.index_name = index_name
        self.storage_name = storage_name
        self.headers = {"Ocp-Apim-Subscription-Key": key}
    def local_search(self,query: str, community_level: int) -> requests.Response:
        url = self.endpoint + "/query/local"
        # optional parameter: community level to query the graph at (default for local query = 2)
        request = {"index_name": self.index_name, "query": query, "community_level": community_level}
        return requests.post(url, json=request, headers=self.headers)
    def global_search(self,query: str, community_level: int) -> requests.Response:
        url = self.endpoint + "/query/global"
        # optional parameter: community level to query the graph at (default for global query = 1)
        request = {"index_name": self.index_name, "query": query, "community_level": community_level}
        return requests.post(url, json=request, headers=self.headers)
    @staticmethod
    def parse_query_response(response: requests.Response, 
                             return_context_data: bool = False) -> requests.Response | dict[list[dict]]:
        if response.ok:
            json_data = json.loads(response.text)
            json_result_data = json_data["result"]
            if return_context_data:
                return json.loads(response.text)["context_data"]
            return json_result_data
        else:
            #Error handling
            print(response.reason)
            print(response.content)
            return response
    @staticmethod
    def extract_source_information(context_information):
        source_map = {}
        sources = ""
        index = 1
        for source in context_information["reports"]:
            if not source["id"] in source_map:
                source_map[source["id"]] = source["title"]
                sources = sources +str(index)+") "+source["title"] + "\n\t"
                index += 1
        return sources

    def upload_batch(self,files: list, overwrite: bool, max_retries: int, url: str) -> requests.Response:
        for i in range(0,max_retries):
            response = requests.post(
                url=url,
                files=files,
                params={"storage_name": self.storage_name, "overwrite": overwrite},
                headers=self.headers,
            )
            # API may be busy, retry
            if response.status_code == 500:
                print("API busy. Sleeping and will try again.")
                time.sleep(10)
                continue
            return response
        
    def upload_files(self,
        file_directory: str,
        batch_size: int = 100,
        overwrite: bool = True,
        max_retries: int = 5,
    ) -> requests.Response | list[Path]:
        url = self.endpoint + "/data"
        batch_files = []
        accepted_file_types = ["text/plain"]
        filepaths = list(Path(file_directory).iterdir())
        for file in tqdm(filepaths):
            # validate that file is a file, has acceptable file type, has a .txt extension, and has utf-8 encoding
            try:
                if (
                    not file.is_file()
                    or file.suffix != ".txt"
                ):
                    print(f"Skipping invalid file: {file}")
                    continue
            except Exception as e:
                print(f"Skipping invalid file: {file}")
                print(e)
            # open and decode file as utf-8, ignore bad characters
            batch_files.append(
                ("files", open(file=file, mode="r", encoding="utf-8", errors="ignore"))
            )
            # upload batch of files
            if len(batch_files) == batch_size:
                response = self.upload_batch(batch_files, overwrite, max_retries, url)
                # if response is not ok, return early
                if not response.ok:
                    return response
                batch_files.clear()
        # upload remaining files
        if len(batch_files) > 0:
            response = self.upload_batch(batch_files, overwrite, max_retries, url)
        return response
    def delete_index(self,container_name: str) -> requests.Response:
        """Delete an azure storage container that holds a search index."""
        url = self.endpoint + f"/index/{container_name}"
        return requests.delete(url, headers=self.headers)

    def check_index_status(self,index_name: str) -> requests.Response:
        url = self.endpoint + f"/index/status/{index_name}"
        return requests.get(url, headers=self.headers)
    
    def build_index(self) -> requests.Response:

        url = self.endpoint + "/index"
        request = {"storage_name": self.storage_name, "index_name": self.index_name}
        return requests.post(url, params=request, headers=self.headers)

def run_test():
    global_query = True
    storage_name = ""
    index_name = ""
    ocp_apim_subscription_key = ""
    """
    "Ocp-Apim-Subscription-Key": 
        This is a custom HTTP header used by Azure API Management service (APIM) to 
        authenticate API requests. The value for this key should be set to the subscription 
        key provided by the Azure APIM instance in your GraphRAG resource group.
    """
    headers = {"Ocp-Apim-Subscription-Key": ocp_apim_subscription_key}
    endpoint = "https://apim-ztsvn4lql4hfq.azure-api.net"
    # perform a global query
    graphRAG_query = RAGHandler(ocp_apim_subscription_key, endpoint, index_name)
    query = "Summarize the main topics found in this data"
    if global_query:
        response = graphRAG_query.global_search(query=query, community_level=1)
    else:
        response = graphRAG_query.local_search(query=query, community_level=2)
    response_data = RAGHandler.parse_query_response(response, return_context_data=True)
    print(response_data)

def main():
   run_test()




# a helper function to parse out the result from a query response

if __name__ == "__main__":
    main()