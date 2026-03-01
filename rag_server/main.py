from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
import ollama, json
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CHROMA_DIR = "./chroma_db"
CHAT_MODEL = "llama3"  
EMBED_MODEL = "nomic-embed-text"

embeddings = OllamaEmbeddings(model=EMBED_MODEL)
vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

def build_prompt(context: str, history: list, question: str) -> list:
    messages = [{"role": "system", "content": f"You are a helpful assistant. Use the following context to answer questions.\n\nContext:\n{context}"}]
    messages += history
    messages.append({"role": "user", "content": question})
    return messages

@app.post("/chat")
async def chat(req: ChatRequest):
    docs = retriever.invoke(req.message)
    context = "\n\n".join(d.page_content for d in docs)
    messages = build_prompt(context, req.history, req.message)

    response = ollama.chat(model=CHAT_MODEL, messages=messages, stream=False)
    answer = response["message"]["content"]
    
    return {"response": answer}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
