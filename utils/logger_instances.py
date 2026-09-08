from utils.logging_utils import set_system_logger

# Shared logger instances to prevent circular imports
folder_processer_logger = set_system_logger("folder_processer", log_file="logs/folder_processing.log")
system_logger = set_system_logger("system_logger", log_file="logs/folder_processing.log")
request_logger = set_system_logger("request_logger", log_file="logs/requests.log")
auth_logger = set_system_logger("auth_logger", log_file="logs/auth.log")
chat_logger = set_system_logger("chat_logger", log_file="logs/chat.log")
db_logger = set_system_logger("db_logger", log_file="logs/database.log")
file_logger = set_system_logger("file_logger", log_file="logs/file_operations.log")
file_convert_logger = set_system_logger("file_convert_logger", log_file="logs/file_conversion.log")
recuriter_interview_logger = set_system_logger("recuriter_interview_logger", log_file="logs/recuriter_interview.log")
