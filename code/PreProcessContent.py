from Utilities import Utilities
import json
def main():
    input_directory = r"C:\Users\dade\Desktop\Pfizer RWE Code With Engagement\local_static_content"
    output_directory = r"C:\Users\dade\Desktop\Pfizer RWE Code With Engagement\raginputdata"
    file_list = Utilities.list_files_in_dir(input_directory)
    for file in file_list:
        filename_only = Utilities.get_filename_only(file)
        filename_without_extension = Utilities.get_file_without_extension(filename_only)
        output_filename = filename_without_extension+".txt"
        with open(input_directory+"\\"+filename_only, "r") as f:
            json_content = json.loads(str(f.read()))
            output_content  = json_content["paragraphs"]+json_content["tables"]
            with open(output_directory+"\\"+output_filename, "w", encoding="utf-8") as f:
                f.write(output_content)
if __name__ == "__main__":
    main()