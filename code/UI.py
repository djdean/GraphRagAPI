from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
import tiktoken
import streamlit as st
from Utilities import Utilities
import json
from RAGHandler import RAGHandler
def main():
    DEBUG = False
    st.set_page_config(layout="wide")
    app_config_path = r"C:\Users\dade\Desktop\GraphRagAPI\config\app_config.json"
    app_config = Utilities.read_json_data(app_config_path)
    aoai_config = Utilities.read_json_data(app_config["aoai_config_path"])
    graphrag_config = Utilities.read_json_data(app_config["graphrag_config_path"])
    document_intelligence_config = Utilities.read_json_data(app_config["document_intelligence_config_path"])
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
    document_intelligence_key = document_intelligence_config["key"]
    document_intelligence_endpoint = document_intelligence_config["endpoint"]
    init_clients(openai_api_version,endpoint,openai_key, document_intelligence_endpoint,document_intelligence_key)
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
            if message['role'] == "Assistant":
                st.markdown(message['content'])
            else:
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
def get_static_content_string(static_content_path, static_cache_path):
    cached_files = Utilities.get_local_cached_files(static_cache_path)
    file_list = Utilities.list_files_in_dir(static_content_path)
    content = ""
    for file in file_list:
        JSON_content = get_or_process_pdf(static_content_path+"\\"+file, st.session_state["DI_client"], cached_files, static_cache_path, static=True)
        content += JSON_content["paragraphs"]+JSON_content["tables"]
    return content
def get_or_process_pdf(uploaded_file,document_intelligence_client, cached_files, local_path, static=False):
    if not static:
        filename = uploaded_file.name
        filename_only = Utilities.get_file_without_extension(filename)
    else:
        filename = uploaded_file
        filename_without_path = Utilities.get_filename_windows_only(filename)
        filename_only = Utilities.get_file_without_extension(filename_without_path)
    
    content = ""
    if filename_only in cached_files:
        cached_file = cached_files[filename_only]
        with open(local_path+"/"+cached_file, "rb") as file:
            document = file.read()
            content = json.loads(document)
    else:
        if not static:
            document = uploaded_file.getvalue()
        else:
            with open(uploaded_file, "rb") as file:
                document = file.read()
        content = parse_pdf(document, document_intelligence_client)
        if not static:
             output_path = local_path+"/"+filename_only+".json"
        else:
            output_filename_only = Utilities.get_file_without_extension(filename_without_path)
            output_path = local_path+"/"+output_filename_only+".json"
        with open(output_path, "w") as file:
            json.dump(content, file)
    return content

def init_clients(openai_api_version,endpoint,openai_key, document_intelligence_endpoint,document_intelligence_key):
    client = AzureOpenAI(
        azure_endpoint = endpoint, 
        api_key=openai_key,  
        api_version=openai_api_version
    )
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint=document_intelligence_endpoint, credential=AzureKeyCredential(document_intelligence_key)
    )
    st.session_state["DI_client"] = document_intelligence_client
    st.session_state["AOAI_client"] = client
    st.session_state["model"] = "gpt-4o"
def get_filename_pretty(path):
     path_split = path.split("\\")
     filename_only = path_split[len(path_split)-1]
     return filename_only
def get_num_tokens_from_string(string: str, encoding_name: str) -> int:
        encoding = tiktoken.encoding_for_model(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
def parse_pdf(doc,document_intelligence_client):
        poller_layout = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout", AnalyzeDocumentRequest(bytes_source=bytes(doc)), locale="en-US"
        )
        layout: AnalyzeResult = poller_layout.result()
        paragraph_content = ""
        table_content = ""
        for p in layout.paragraphs:
            paragraph_content += f"{p.content}\n"
        for t in layout.tables:
            previous_cell_row=0
            rowcontent='| '
            tablecontent = ''
            for c in t.cells:
                if c.row_index == previous_cell_row:
                    rowcontent +=  c.content + " | "
                else:
                    tablecontent += rowcontent + "\n"
                    rowcontent='|'
                    rowcontent += c.content + " | "
                    previous_cell_row += 1
            table_content += f"{tablecontent}\n"
        return_content = {
            "paragraphs": paragraph_content,
            "tables": table_content
        }
        return return_content
def answer_question(question,client, model,context, history):
        response = client.chat.completions.create(
            model=model, # model = "deployment_name".
            messages=[
                {"role": "system", "content": "You are an AI reearch assistant extremely proficient at answering research-centric questions. Asthma is one area in particular you know a lot about."},
                {"role": "user", "content": "Based on the following context:\n\n"+context+"\
                 \n\n Along with the user's chat history:\n\n"+history+"\n\nAnswer the following question:\n\n"+question+".\
                  Please include as many details as possible including references if applicable."\
                }
            ]
        )
        return response.choices[0].message.content
if __name__ == "__main__":
    main()

