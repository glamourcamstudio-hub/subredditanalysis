import streamlit as st
import praw
from groq import Groq
import json
import os

# ==================== CONFIGURACIÓN ====================
# Secrets desde Streamlit Cloud (agrega en settings)
REDDIT_CLIENT_ID = st.secrets["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET = st.secrets["REDDIT_CLIENT_SECRET"]
REDDIT_USER_AGENT = st.secrets["REDDIT_USER_AGENT"]
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

GROQ_MODEL = "llama-3.1-70b-versatile"  # Bueno para JSON estructurado, gratis en free tier

client = Groq(api_key=GROQ_API_KEY)

# Tus stats default (editable en UI)
DEFAULT_KARMA_POST = 300
DEFAULT_KARMA_COMMENT = 150
DEFAULT_DIAS_CUENTA = 180

# Schema JSON expandido para análisis completo
SCHEMA = {
    "type": "object",
    "properties": {
        "subreddit": {"type": "string"},
        "karma_post_min": {"type": ["number", "null"]},
        "karma_comment_min": {"type": ["number", "null"]},
        "karma_total_min": {"type": ["number", "null"]},
        "account_age_days_min": {"type": ["number", "null"]},
        "account_age_months_min": {"type": ["number", "null"]},
        "verification_required": {"type": "boolean"},
        "verification_method": {"type": ["string", "null"]},
        "promotion_allowed": {"type": "string", "enum": ["Sí", "Solo teasers", "Solo verificados", "No"]},
        "link_directo_of": {"type": "boolean"},
        "frecuencia_max": {"type": ["string", "null"]},
        "flair_obligatorio": {"type": ["string", "null"]},
        "tipo_contenido_permitido": {"type": ["array", "null"], "items": {"type": "string"}},
        "prohibiciones_clave": {"type": ["array", "null"], "items": {"type": "string"}},
        "formato_post_obligatorio": {"type": ["string", "null"]},
        "automod_filtros": {"type": ["array", "null"], "items": {"type": "string"}},
        "nivel_actividad": {"type": ["string", "null"]},
        "tamanio_sub": {"type": ["number", "null"]},
        "moderacion_estricta": {"type": "boolean"},
        "reglas_mas_relevantes": {"type": ["array", "null"], "items": {"type": "string"}},
        "otras_restricciones_importantes": {"type": ["array", "null"], "items": {"type": "string"}},
        "diagnostico_tu_cuenta": {"type": "string", "enum": ["VERDE", "AMARILLO", "ROJO"]},
        "razon_diagnostico": {"type": "string"},
        "estrategia_recomendada": {"type": "string"},
        "riesgo_shadowban": {"type": ["string", "null"]},
        "potencial_marketing": {"type": ["string", "null"]}
    },
    "required": ["subreddit", "diagnostico_tu_cuenta", "razon_diagnostico", "estrategia_recomendada"]
}

# ==================== FUNCIONES ====================
def analizar_reglas(sub_name, karma_post, karma_comment, dias_cuenta):
    sub_name = sub_name.replace("r/", "").strip()
    sub = reddit.subreddit(sub_name)
    
    reglas_texto = "\n".join([f"Regla {i+1}: {r.short_name} - {r.description}" for i, r in enumerate(sub.rules)])
    sidebar = sub.description or sub.public_description or ""
    subscribers = sub.subscribers
    
    texto_completo = f"SUBREDDIT: r/{sub.display_name}\nSUSCRIPTORES: {subscribers}\nREGLAS:\n{reglas_texto}\nSIDEBAR:\n{sidebar}"
    
    prompt = f"""
Eres experto en reglas de Reddit para promoción NSFW/OnlyFans 2026.
Analiza el texto y extrae datos precisos.

Texto:
{texto_completo}

Responde SOLO con JSON válido siguiendo este schema:
{json.dumps(SCHEMA, indent=2)}

Null si no mencionado. Booleanos: true/false.
Diagnóstico basado en karma post: {karma_post}, comment: {karma_comment}, días: {dias_cuenta}.
Potencial marketing: Alto si permite promo + actividad alta.
"""
    
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.0
    )
    
    return json.loads(response.choices[0].message.content)

def analizar_top_posts(sub_name):
    sub = reddit.subreddit(sub_name.replace("r/", ""))
    top_posts = sub.top(limit=10)
    
    posts_texto = "\n".join([f"Post {i+1}: Título: {p.title} | Upvotes: {p.score} | Comentarios: {p.num_comments} | URL: {p.url}" for i, p in enumerate(top_posts, 1)])
    
    prompt = """
Eres experto en análisis de posts Reddit para marketing OnlyFans.
Analiza estos top 10 posts:

{posts_texto}

Responde en JSON:
{{
  "top_posts_resumen": ["lista de 10 strings con título + upvotes + comentarios"],
  "analisis_mejores": "explicación de qué hace exitosos a los top posts (títulos atractivos, tipo contenido, engagement, estrategia recomendada)"
}}
"""
    
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt.format(posts_texto=posts_texto)}],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    
    return json.loads(response.choices[0].message.content)

# ==================== INTERFAZ STREAMLIT ====================
st.set_page_config(page_title="Analizador Subreddits OnlyFans", layout="wide")

st.title("Analizador de Subreddits para OnlyFans / NSFW 🔥")
st.markdown("Ingresa un subreddit para análisis de reglas, diagnóstico y top posts.")

col1, col2 = st.columns([3, 2])

with col1:
    subreddit_input = st.text_input("Subreddit (ej: r/OnlyFansPromotions)", "")
    analizar_btn = st.button("Analizar", type="primary")

with col2:
    st.subheader("Tus stats")
    karma_post = st.number_input("Post Karma", min_value=0, value=DEFAULT_KARMA_POST)
    karma_comment = st.number_input("Comment Karma", min_value=0, value=DEFAULT_KARMA_COMMENT)
    dias_cuenta = st.number_input("Días de cuenta", min_value=0, value=DEFAULT_DIAS_CUENTA)

if analizar_btn and subreddit_input:
    with st.spinner("Analizando reglas y top posts con IA..."):
        try:
            resultado_reglas = analizar_reglas(subreddit_input, karma_post, karma_comment, dias_cuenta)
            resultado_posts = analizar_top_posts(subreddit_input)
            
            # Mostrar diagnóstico
            diag = resultado_reglas['diagnostico_tu_cuenta']
            color = {"VERDE": "green", "AMARILLO": "orange", "ROJO": "red"}.get(diag, "gray")
            st.markdown(f"### 🔴 DIAGNÓSTICO: :{color}[{diag}]")
            st.markdown(f"*Razón:* {resultado_reglas['razon_diagnostico']}")
            
            st.markdown("### ✅ REQUISITOS OBLIGATORIOS")
            reqs = [
                f"Karma mínimo: {resultado_reglas['karma_post_min']} post + {resultado_reglas['karma_comment_min']} comment (total {resultado_reglas['karma_total_min']})",
                f"Edad cuenta: {resultado_reglas['account_age_days_min']} días ({resultado_reglas['account_age_months_min']} meses)",
                f"Verificación: {'Obligatoria' if resultado_reglas['verification_required'] else 'No'} ({resultado_reglas['verification_method']})",
                f"Abierto para: {resultado_reglas['promotion_allowed']}",
                f"Frecuencia: {resultado_reglas['frecuencia_max']}",
                f"Formato: {resultado_reglas['formato_post_obligatorio']} + flair {resultado_reglas['flair_obligatorio']}"
            ]
            for req in reqs:
                if req: st.markdown(f"• {req}")
            
            st.markdown("### 🚀 ESTRATEGIA RECOMENDADA")
            st.info(resultado_reglas['estrategia_recomendada'])
            
            # Top posts
            st.subheader("Top 10 Posts")
            for post in resultado_posts['top_posts_resumen']:
                st.markdown(f"- {post}")
            
            st.subheader("Análisis de Mejores Posts")
            st.info(resultado_posts['analisis_mejores'])
            
            # Más detalles
            with st.expander("Detalles completos (JSON)"):
                st.json(resultado_reglas)
        
        except Exception as e:
            st.error(f"Error: {str(e)}. Verifica keys o subreddit.")

st.caption("Desplegado en Streamlit Cloud | Groq IA gratis | 2026")