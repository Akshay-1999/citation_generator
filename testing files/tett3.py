import requests
import json

# Replace with your actual local server URL
BASE_URL = "http://localhost:8000"

def test_folder_processing():
    # You'll need to be logged in to get a session cookie. 
    # Or, if you have a way to bypass auth for testing, use that.
    # For now, I'll assume you run this manually with a valid auth cookie or after logging in.
    
    # Example folder path - CHANGE THIS to a real local path on your machine
    folder_path = r"d:\Akshay\Work and Document\Training\LLM AND AI\citation\citation_generator\test_folder"
    
    # Create the test folder if it doesn't exist (for demonstration)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created test folder: {folder_path}")
    
    endpoint = f"{BASE_URL}/folder/process_folder"
    
    payload = {
        "folder_path": folder_path
    }
    
    # To run this script effectively, you might need to provide the 'auth_token' cookie
    # cookies = {"auth_token": "YOUR_TOKEN_HERE"}
    # response = requests.post(endpoint, json=payload, cookies=cookies)
    
    print(f"Testing endpoint: {endpoint}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    print("\nTo verify this manually, use a tool like Postman or the Browser DevTools console:")
    print(f"""
    fetch('{endpoint}', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json'
        }},
        body: JSON.stringify({payload})
    }})
    .then(r => r.json())
    .then(console.log);
    """)

if __name__ == "__main__":
    import os
    test_folder_processing()
