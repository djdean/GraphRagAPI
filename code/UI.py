from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
import tiktoken
import streamlit as st
from Utilities import Utilities
import json
from RAGHandler import RAGHandler
def main():
    DEBUG = True
    STATIC_DEPLOY = False
    st.set_page_config(layout="wide")
    if STATIC_DEPLOY:
        pass
    else:
        app_config_path = r"C:\Users\dade\Desktop\GraphRagAPI\config\app_config_keytruda_limited.json"
        app_config = Utilities.read_json_data(app_config_path)
        graphrag_config = Utilities.read_json_data(app_config["graphrag_config_path"])
        aoai_config = Utilities.read_json_data(app_config["aoai_config_path"])
    endpoint = aoai_config["endpoint"]
    openai_key = aoai_config["key"]
    openai_api_version = aoai_config["api_version"]
    model = aoai_config["model"]
    model_family = aoai_config["model_family"]
    with st.sidebar:
        use_RAG = st.checkbox("Use GraphRAG for additional content?", value=True)
        global_or_local = st.selectbox("Use local or global search?",["Local","Global"])
        local = True
        if global_or_local == "Global":
            local = False
        st.write("Model Family: "+model_family)
        st.write("Model: "+model)
    init_clients(openai_api_version,endpoint,openai_key,model)
    RAGQuery_object = init_RAG_query(graphrag_config)
    if not use_RAG:
        with st.sidebar:
            st.write("GraphRAG is not being used.")
    else:
        with st.sidebar:
            st.write("GraphRAG is being used. No static content loaded.")
            st.write("Using search mechanism: "+("local" if local else "global"))
    query_type = "global query" if not local else "local query"

    if not "messages" in st.session_state:
            st.session_state["messages"] = []
    question = st.chat_input("Question:")
    messages = st.session_state["messages"]
    history = ""
    for message in messages:
        history += message['content']
        with st.chat_message(message['role']):
                st.markdown(message['content'])
    if question:
        context = ""
        if use_RAG:
            with st.spinner(f"Searching for context using GraphRAG {query_type}..."):
                query_results = ""
                if local:
                    query_results = RAGQuery_object.local_search(question,2)
                else:
                    query_results = RAGQuery_object.global_search(question,1)
            context = RAGHandler.parse_query_response(query_results, return_context_data=False)
            if DEBUG:
                print(context)
        with st.spinner("Answering Question..."):
            handle_question(question,model,context,history)

def handle_question(question,model,context,history):
    answer = answer_question(question,st.session_state["AOAI_client"],model, context, history)
    user_message = {
        "role":"user",
        "content":question
    }
    st.session_state["messages"].append(user_message)
    with st.chat_message(user_message["role"]):
        st.markdown(user_message['content'])
    response_message = {
        "role":"Assistant",
        "content":answer,
    }
    with st.chat_message(response_message["role"]):
        st.markdown(response_message['content'])
    st.session_state["messages"].append(response_message) 
def init_RAG_query(graphrag_config):
    graphrag_endpoint = graphrag_config["endpoint"]
    graphrag_key = graphrag_config["key"]
    graphrag_index_name = graphrag_config["index_name"]
    graphrag_storage_name = graphrag_config["storage_name"]
    RAGQuery_object = RAGHandler(key=graphrag_key,endpoint=graphrag_endpoint,
                                 storage_name=graphrag_storage_name,index_name=graphrag_index_name)
    return RAGQuery_object

def init_clients(openai_api_version,endpoint,openai_key,aoai_model):
    client = AzureOpenAI(
        azure_endpoint = endpoint, 
        api_key=openai_key,  
        api_version=openai_api_version
    )
    
    st.session_state["AOAI_client"] = client
    st.session_state["model"] = aoai_model
def get_filename_pretty(path):
     path_split = path.split("\\")
     filename_only = path_split[len(path_split)-1]
     return filename_only
def get_num_tokens_from_string(string: str, encoding_name: str) -> int:
        encoding = tiktoken.encoding_for_model(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
def answer_question(question,client, model,context, history):
        response = client.chat.completions.create(
            model=model, # model = "deployment_name".
            messages=[
                {"role": "system", "content": "You are an AI reearch assistant extremely proficient at answering research-centric questions. Alzheimer's is one area in particular you know a lot about.\n"},
                {"role": "user", "content": "Based on the following context:\n\n"+context+"\
                 \n\n Along with the user's chat history:\n\n"+history+"\n\nAnswer the following question:\n\n"+question+".\
                  Please include as many details as possible including references if applicable. Only base your reply on the data provided as content, do not include other data."\
                }
            ]
        )
        return response.choices[0].message.content
if __name__ == "__main__":
    main()

