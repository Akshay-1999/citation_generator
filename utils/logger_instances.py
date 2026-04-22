from utils.logging_utils import set_system_logger

# Shared logger instances to prevent circular imports
folder_processer_logger = set_system_logger("folder_processer", log_file="logs/folder_processing.log")
system_logger = set_system_logger("system_logger", log_file="logs/folder_processing.log")
request_logger = set_system_logger("request_logger", log_file="logs/requests.log")
