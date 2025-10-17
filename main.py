from fastapi import FastAPI, HTTPException
import redis
import os
import json
import requests
from datetime import datetime
from supabase import create_client, Client
import google.generativeai as genai
import openai

app = FastAPI(
    title="Leonor AI API",
    description="Multi-provider AI API with Gemini, Supabase, Redis & OpenRouter",
    version="2.1.0"
)

# =============================================================================
# CONFIGURAÇÃO DE TODOS OS CLIENTES
# =============================================================================

# Configurar Redis
redis_client = None
try:
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        redis_client = redis.from_url(redis_url)
        redis_client.ping()
        print("✅ Redis conectado!")
    else:
        print("❌ REDIS_URL não configurada")
except Exception as e:
    print(f"❌ Erro Redis: {e}")

# Configurar Supabase
supabase_client = None
try:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if supabase_url and supabase_key:
        supabase_client = create_client(supabase_url, supabase_key)
        print("✅ Supabase conectado!")
    else:
        print("❌ Variáveis Supabase não configuradas")
except Exception as e:
    print(f"❌ Erro Supabase: {e}")

# Configurar Gemini
gemini_client = None
try:
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        genai.configure(api_key=gemini_key)
        gemini_client = genai
        print("✅ Gemini configurado!")
    else:
        print("❌ GEMINI_API_KEY não configurada")
except Exception as e:
    print(f"❌ Erro Gemini: {e}")

# Configurar OpenRouter
openrouter_client = None
try:
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        openai.api_base = "https://openrouter.ai/api/v1"
        openai.api_key = openrouter_key
        openrouter_client = openai
        print("✅ OpenRouter configurado!")
    else:
        print("❌ OPENROUTER_API_KEY não configurada")
except Exception as e:
    print(f"❌ Erro OpenRouter: {e}")

# =============================================================================
# ENDPOINTS PRINCIPAIS
# =============================================================================

@app.get("/")
async def root():
    return {
        "status": "online", 
        "service": "Leonor AI Multi-Provider",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.1.0",
        "services_available": {
            "redis": redis_client is not None,
            "supabase": supabase_client is not None,
            "gemini": gemini_client is not None,
            "openrouter": openrouter_client is not None,
            "tavily": bool(os.getenv("TAVILY_API_KEY"))
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# =============================================================================
# ENDPOINTS REDIS
# =============================================================================

@app.get("/test-redis")
async def test_redis():
    if not redis_client:
        return {"status": "error", "message": "Redis não configurado"}
    
    try:
        test_data = {
            "message": "Teste Redis - Leonor AI",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "Multi-Provider API"
        }
        
        redis_client.setex("leonor_test", 300, json.dumps(test_data))
        result = redis_client.get("leonor_test")
        
        return {
            "status": "success",
            "service": "redis",
            "data_written": test_data,
            "data_read": json.loads(result) if result else None,
            "message": "✅ Redis funcionando!"
        }
    except Exception as e:
        return {"status": "error", "service": "redis", "error": str(e)}

# =============================================================================
# ENDPOINTS SUPABASE
# =============================================================================

@app.get("/test-supabase")
async def test_supabase():
    if not supabase_client:
        return {"status": "error", "message": "Supabase não configurado"}
    
    try:
        table_name = "leonor_ai_tests"
        test_data = {
            "message": "Teste de conexão Supabase",
            "created_at": datetime.utcnow().isoformat(),
            "service": "Leonor AI API"
        }
        
        # Inserir dados
        insert_response = supabase_client.table(table_name).insert(test_data).execute()
        
        # Ler dados
        select_response = supabase_client.table(table_name).select("*").execute()
        
        return {
            "status": "success",
            "service": "supabase",
            "inserted": insert_response.data,
            "all_records": select_response.data,
            "message": "✅ Supabase funcionando!"
        }
    except Exception as e:
        return {"status": "error", "service": "supabase", "error": str(e)}

# =============================================================================
# ENDPOINTS GEMINI
# =============================================================================

@app.post("/gemini/chat")
async def gemini_chat(prompt: str, model: str = "gemini-pro"):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="Gemini não configurado")
    
    try:
        model_instance = genai.GenerativeModel(model)
        response = model_instance.generate_content(prompt)
        
        # Salvar no Redis para cache
        if redis_client:
            cache_key = f"gemini:{hash(prompt)}"
            redis_client.setex(cache_key, 3600, response.text)
        
        return {
            "status": "success",
            "service": "gemini",
            "model": model,
            "response": response.text,
            "cached": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro Gemini: {str(e)}")

@app.get("/test-gemini")
async def test_gemini():
    if not gemini_client:
        return {"status": "error", "message": "Gemini não configurado"}
    
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content("Explique em uma frase o que é inteligência artificial.")
        
        return {
            "status": "success", 
            "service": "gemini",
            "response": response.text,
            "message": "✅ Gemini funcionando!"
        }
    except Exception as e:
        return {"status": "error", "service": "gemini", "error": str(e)}

# =============================================================================
# ENDPOINTS OPENROUTER
# =============================================================================

@app.post("/openrouter/chat")
async def openrouter_chat(prompt: str, model: str = "deepseek/deepseek-coder"):
    if not openrouter_client:
        raise HTTPException(status_code=500, detail="OpenRouter não configurado")
    
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        
        ai_response = response.choices[0].message.content
        
        # Cache no Redis
        if redis_client:
            cache_key = f"openrouter:{hash(prompt)}"
            redis_client.setex(cache_key, 3600, ai_response)
        
        return {
            "status": "success",
            "service": "openrouter",
            "model": model,
            "response": ai_response,
            "cached": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro OpenRouter: {str(e)}")

@app.get("/test-openrouter")
async def test_openrouter():
    if not openrouter_client:
        return {"status": "error", "message": "OpenRouter não configurado"}
    
    try:
        response = openai.ChatCompletion.create(
            model="deepseek/deepseek-coder",
            messages=[{"role": "user", "content": "Escreva 'Hello World' em Python"}]
        )
        
        return {
            "status": "success",
            "service": "openrouter",
            "response": response.choices[0].message.content,
            "model": "deepseek/deepseek-coder",
            "message": "✅ OpenRouter funcionando!"
        }
    except Exception as e:
        return {"status": "error", "service": "openrouter", "error": str(e)}

# =============================================================================
# ENDPOINTS TAVILY (PESQUISA WEB)
# =============================================================================

@app.get("/tavily/search")
async def tavily_search(query: str = "últimas notícias de IA"):
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        raise HTTPException(status_code=500, detail="Tavily não configurado")
    
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 5
            }
        )
        
        if response.status_code == 200:
            return {
                "status": "success",
                "service": "tavily",
                "query": query,
                "results": response.json()
            }
        else:
            return {
                "status": "error",
                "service": "tavily",
                "error": f"API retornou status {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro Tavily: {str(e)}")

# =============================================================================
# ENDPOINT DE ORQUESTRAÇÃO - MULTI-AI
# =============================================================================

@app.post("/ai/chat")
async def multi_ai_chat(prompt: str, provider: str = "gemini"):
    """Endpoint unificado para todos os provedores de IA"""
    
    # Cache check
    if redis_client:
        cache_key = f"ai_chat:{hash(prompt)}:{provider}"
        cached = redis_client.get(cache_key)
        if cached:
            return {
                "status": "success",
                "provider": provider,
                "response": cached.decode(),
                "cached": True
            }
    
    try:
        if provider == "gemini" and gemini_client:
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(prompt)
            ai_response = response.text
            
        elif provider == "openrouter" and openrouter_client:
            response = openai.ChatCompletion.create(
                model="deepseek/deepseek-coder",
                messages=[{"role": "user", "content": prompt}]
            )
            ai_response = response.choices[0].message.content
            
        else:
            raise HTTPException(status_code=400, detail=f"Provedor {provider} não disponível")
        
        # Save to cache
        if redis_client:
            redis_client.setex(cache_key, 3600, ai_response)
        
        return {
            "status": "success",
            "provider": provider,
            "response": ai_response,
            "cached": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro com {provider}: {str(e)}")

# =============================================================================
# ENDPOINT DE DEBUG COMPLETO
# =============================================================================

@app.get("/debug")
async def debug():
    return {
        "environment": {
            "REDIS_URL": "✅ SET" if os.getenv("REDIS_URL") else "❌ MISSING",
            "SUPABASE_URL": "✅ SET" if os.getenv("SUPABASE_URL") else "❌ MISSING", 
            "SUPABASE_KEY": "✅ SET" if os.getenv("SUPABASE_KEY") else "❌ MISSING",
            "GEMINI_API_KEY": "✅ SET" if os.getenv("GEMINI_API_KEY") else "❌ MISSING",
            "TAVILY_API_KEY": "✅ SET" if os.getenv("TAVILY_API_KEY") else "❌ MISSING",
            "OPENROUTER_API_KEY": "✅ SET" if os.getenv("OPENROUTER_API_KEY") else "❌ MISSING",
            "DEEPSEEK_API_KEY": "✅ SET" if os.getenv("DEEPSEEK_API_KEY") else "❌ MISSING"
        },
        "services_status": {
            "redis": redis_client is not None,
            "supabase": supabase_client is not None,
            "gemini": gemini_client is not None,
            "openrouter": openrouter_client is not None
        },
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.1.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
