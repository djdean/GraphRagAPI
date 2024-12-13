import requests
import json

class RAGQuery:
    def __init__(self, ocp_apim_subscription_key: str, endpoint: str, index_name: str | list[str]):
        self.ocp_apim_subscription_key = ocp_apim_subscription_key
        self.endpoint = endpoint
        self.index_name = index_name
        self.headers = {"Ocp-Apim-Subscription-Key": ocp_apim_subscription_key}
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

def main():
    global_query = True
    storage_name = "raginputdata"
    index_name = "graphrRAGindex"
    ocp_apim_subscription_key = "0c46a21bb1d14f309981a1dcab7b271e"
    """
    "Ocp-Apim-Subscription-Key": 
        This is a custom HTTP header used by Azure API Management service (APIM) to 
        authenticate API requests. The value for this key should be set to the subscription 
        key provided by the Azure APIM instance in your GraphRAG resource group.
    """
    headers = {"Ocp-Apim-Subscription-Key": ocp_apim_subscription_key}
    endpoint = "https://apim-ztsvn4lql4hfq.azure-api.net"
    # perform a global query
    graphRAG_query = RAGQuery(ocp_apim_subscription_key, endpoint, index_name)
    query = "Summarize the main topics found in this data"
    if global_query:
        response = graphRAG_query.global_search(query=query, community_level=1)
    else:
        response = graphRAG_query.local_search(query=query, community_level=2)
    response_data = RAGQuery.parse_query_response(response, return_context_data=True)
    print(response_data)



# a helper function to parse out the result from a query response

if __name__ == "__main__":
    main()