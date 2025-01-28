import os
import json
class Utilities:
    def __init__(self):
        pass
    @staticmethod
    def get_local_cached_files(path):
        file_list = os.listdir(path)
        cached_files = {}
        for file in file_list:
            file_without_path = Utilities.get_filename_only(file)
            file_without_extension = Utilities.get_file_without_extension(file_without_path)
            cached_files[file_without_extension] = file
        return cached_files
    @staticmethod
    def read_json_data(file_name):
        with open(file_name) as json_file:
            data = json.load(json_file)
        return data
    @staticmethod
    def get_filename_only(filename_with_path):
        return filename_with_path.split("/")[-1]
    @staticmethod
    def get_filename_windows_only(filename_with_path):
        return filename_with_path.split("\\")[-1]
    @staticmethod
    def get_file_without_extension(filename):
        return filename.split(".")[0]
    @staticmethod
    def list_files_in_dir(path):
        return os.listdir(path)