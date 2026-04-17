# Citation Generator

An AI-powered application for generating resume mappings and citations using FastAPI (Backend) and React + Vite (Frontend).

## 🚀 Getting Started

Follow these instructions to set up the project locally on your machine.

### Prerequisites

- **Python**: 3.9 or higher
- **Node.js**: 18.0 or higher
- **PostgreSQL**: Local or remote instance
- **Vector DB**: Pinecone account (for index creation)

---

## 🛠️ Backend Setup (FastAPI)

### 1. Clone the repository
```bash
git clone https://github.com/Akshay-1999/citation_generator.git
cd citation_generator
```

### 2. Create a Virtual Environment
```bash
# On Windows
python -m venv venv

# On macOS/Linux
python3 -m venv venv
```

### 3. Activate the Virtual Environment
```bash
# On Windows
.\venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Create a `.env` file in the root directory and add the following keys. You can use `.env.example` as a template:

```bash
cp .env.example .env
```

Fill in the following variables:
- `db_user`, `db_password`, `db_host`, `db_port`, `db_name` (PostgreSQL credentials)
- `openai_api_key` (OpenAI API key)
- `secret_key` (Random string for authentication)
- `TAVILY_API_KEY` (Tavily search API)
- `PINECONE_API_KEY` & `PINECONE_INDEX_NAME` (Vector storage)
- `COHERE_API_KEY` (Reranking/Embeddings)
- `LANGSMITH_API_KEY` (Optional for tracing)

### 6. Run the Backend Server
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
The API documentation will be available at `http://localhost:8000/docs`.

---

## 💻 Frontend Setup (React + Vite)

### 1. Navigate to the frontend directory
```bash
cd frontend
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Run the Development Server
```bash
npm run dev
```
The application will be accessible at `http://localhost:5173`.

---

## 📁 Project Structure

- `app.py`: Main FastAPI entry point
- `agents/`: AI agent logic and tools
- `db/`: Database models and connection setup
- `frontend/`: React + Vite application
- `requirements.txt`: Python package dependencies
- `static/` & `uploaded_files/`: Static assets and processed documents

## 📄 License
This project is for training and development purposes.

## Production Deployment

### 1. Build the Frontend
```bash
cd frontend
npm run build
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory and add the following keys. You can use `.env.example` as a template:

```bash
cp .env.example .env
```

Fill in the following variables:
- `db_user`, `db_password`, `db_host`, `db_port`, `db_name` (PostgreSQL credentials)
- `openai_api_key` (OpenAI API key)
- `secret_key` (Random string for authentication)
- `TAVILY_API_KEY` (Tavily search API)
- `PINECONE_API_KEY` & `PINECONE_INDEX_NAME` (Vector storage)
- `COHERE_API_KEY` (Reranking/Embeddings)
- `LANGSMITH_API_KEY` (Optional for tracing)

### 3. Run the Backend Server
```bash
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker -b [IP_ADDRESS]:8000
```
The API documentation will be available at `http://[IP_ADDRESS]/docs`.


### deploy
bash
./deploy.sh

### start the server
bash
sudo systemctl start fastapi

### stop the server
bash
sudo systemctl stop fastapi

### read logs
🛠️ Step 4: Check Status & Logs
bash
sudo systemctl status fastapi
Logs:

bash
journalctl -u fastapi -f
