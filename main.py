
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
import json
from datetime import datetime

app = FastAPI(title="Leonor AI API", version="1.0.0")

# Models
class ChatRequest(BaseModel):
    message: str
    searchEnabled: bool = False

class ChatResponse(BaseModel):
    success: bool
    response: str
    search_used: bool
    timestamp: str

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/")
async def root():
    return {
        "status": "active", 
        "message": "Leonor AI API running", 
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

# Health endpoint
@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "service": "leonor-ai",
        "timestamp": datetime.utcnow().isoformat()
    }

# 🔍 FUNÇÃO DE BUSCA TAVILY (síncrona)
def search_tavily(query: str, api_key: str):
    try:
        print(f"🔍 Buscando no Tavily: {query}")
        
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": 3
            },
            timeout=30
        )
        
        print(f"📡 Status Tavily: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Busca Tavily bem-sucedida: {len(data.get('results', []))} resultados")
            return data
        else:
            error_msg = f"Erro na busca: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
            
    except Exception as e:
        error_msg = f"Erro ao conectar com Tavily: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

# ✅ ROTA CHAT - CORRIGIDA E MELHORADA
@app.post("/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        print(f"📨 Recebida mensagem: '{request.message}' | Busca: {request.searchEnabled}")
        
        # 🔍 BUSCA COM TAVILY SE SOLICITADO
        search_results = None
        if request.searchEnabled:
            tavily_key = os.getenv("TAVILY_API_KEY")
            print(f"🔑 Tavily Key configurada: {bool(tavily_key)}")
            
            if tavily_key:
                # Chamada síncrona, sem await
                search_results = search_tavily(request.message, tavily_key)
            else:
                print("❌ TAVILY_API_KEY não encontrada nas variáveis de ambiente")
        
        # 🤖 RESPOSTA DA IA
        response_text = f"Olá! Recebi sua mensagem: '{request.message}'"
        
        if search_results and "results" in search_results:
            # Formata os resultados de busca
            results_text = "\n".join([
                f"• {result['title']}: {result['content'][:100]}..." 
                for result in search_results["results"][:2]  # Limita a 2 resultados
            ])
            response_text += f"\n\n🔍 Encontrei estas informações:\n{results_text}"
        elif search_results and "error" in search_results:
            response_text += f"\n\n⚠️ Busca não disponível: {search_results['error']}"
        
        return {
            "success": True,
            "response": response_text,
            "search_used": bool(search_results and "results" in search_results),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Erro no endpoint /v1/chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# ✅ ROTA PARA TESTAR TAVILY
@app.get("/test-tavily")
async def test_tavily():
    api_key = os.getenv("TAVILY_API_KEY")
    
    print(f"🔑 Verificando TAVILY_API_KEY: {bool(api_key)}")
    
    if not api_key:
        return {
            "success": False,
            "error": "TAVILY_API_KEY não configurada",
            "environment_variables": dict(os.environ)  # Debug: mostra todas as variáveis
        }
    
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": "teste de conexão Leonor AI",
                "max_results": 1
            },
            timeout=30
        )
        
        result = {
            "success": response.status_code == 200,
            "api_key_set": True,
            "tavily_status": response.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if response.status_code == 200:
            result["response"] = response.json()
        else:
            result["error"] = response.text
            
        return result
        
    except Exception as e:
        return {
            "success": False, 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# ✅ NOVA ROTA: LISTAR PROVEDORES DISPONÍVEIS
@app.get("/providers")
async def list_providers():
    return {
        "providers": {
            "tavily_search": bool(os.getenv("TAVILY_API_KEY")),
            "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
            "huggingface": bool(os.getenv("HUGGINGFACE_TOKEN")),
            "openrouter": bool(os.getenv("OPENROUTER_API_KEY"))
        },
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
