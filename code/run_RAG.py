from Utilities import Utilities
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from RAGHandler import RAGHandler
import json
import time

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
def parse_pdfs(input_directory,output_directory,document_intelligence_client):
    file_list = Utilities.list_files_in_dir(input_directory)
    for file in file_list:
        filename_only = Utilities.get_filename_only(file)
        filename_without_extension = Utilities.get_file_without_extension(filename_only)
        output_filename = filename_without_extension+".json"
        with open(input_directory+"\\"+filename_only, mode="rb") as f:
            doc = f.read()
            json_content = parse_pdf(doc,document_intelligence_client)
            with open(output_directory+"\\"+output_filename, "w", encoding="utf-8") as f:
                f.write(json.dumps(json_content))
def format_output(input_directory,output_directory):
    file_list = Utilities.list_files_in_dir(input_directory)
    for file in file_list:
        filename_only = Utilities.get_filename_only(file)
        filename_without_extension = Utilities.get_file_without_extension(filename_only)
        output_filename = filename_without_extension+".txt"
        with open(input_directory+"\\"+filename_only, mode="r",encoding="utf-8") as f:
            json_content = json.loads(str(f.read()))
            output_content  = json_content["paragraphs"]+json_content["tables"]
            with open(output_directory+"\\"+output_filename, "w", encoding="utf-8") as f:
                f.write(output_content)
def main():
    prepare_data = False
    upload_data = False
    app_config_path = r"C:\Users\dade\Desktop\GraphRagAPI\config\app_config_labcorp.json"
    app_config = Utilities.read_json_data(app_config_path)
    graphrag_config = Utilities.read_json_data(app_config["graphrag_config_path"])
    document_intelligence_config = Utilities.read_json_data(app_config["document_intelligence_config_path"])
    raw_input_directory = app_config["raw_input_directory"]
    rag_input_directory = app_config["rag_input_directory"]
    json_output_directory = app_config["json_output_directory"]
    document_intelligence_key = document_intelligence_config["key"]
    document_intelligence_endpoint = document_intelligence_config["endpoint"]
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint=document_intelligence_endpoint, credential=AzureKeyCredential(document_intelligence_key)
    )
    if prepare_data:
        parse_pdfs(raw_input_directory,json_output_directory,document_intelligence_client)
        format_output(json_output_directory,rag_input_directory)
    else:
        graphrag_endpoint = graphrag_config["endpoint"]
        graphrag_key = graphrag_config["key"]
        graphrag_storage_name = graphrag_config["storage_name"]
        graphrag_index_name = graphrag_config["index_name"]
        graphrag_handler = RAGHandler(graphrag_key,graphrag_endpoint,graphrag_storage_name,graphrag_index_name)
        if upload_data:
            print("Uploading files")
            upload_response = graphrag_handler.upload_files(rag_input_directory)
            print(upload_response)
            print("Building index")
            build_response = graphrag_handler.build_index()
            print(build_response)
        while True:
            status_response = graphrag_handler.check_index_status(graphrag_index_name)
            print(status_response.json()["status"])
            if status_response.json()["status"] == "complete":
                break
            time.sleep(10)
if __name__ == "__main__":
    main()