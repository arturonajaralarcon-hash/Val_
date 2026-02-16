import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
from io import BytesIO
import json
import os
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Valeria Desvelada AI Studio", layout="wide", page_icon="💃")

# --- FUNCIONES DE UTILIDAD (UPSCALING) ---
def upscale_image(image, target_width=3840): # 4K
    """
    Reescala usando algoritmo LANCZOS (Alta fidelidad fotográfica).
    """
    w_percent = (target_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    img_resized = image.resize((target_width, h_size), PIL.Image.Resampling.LANCZOS)
    return img_resized

# --- CARGADOR DE DATOS JSON ---
@st.cache_data
def load_json_data(folder_path="data"):
    data_context = {}
    if not os.path.exists(folder_path):
        return None, "⚠️ Carpeta 'data' no encontrada."
    
    files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    if not files:
        return None, "⚠️ Carpeta 'data' vacía."

    try:
        for filename in files:
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                category_name = filename.replace('.json', '')
                data_context[category_name] = json.load(f)
        return data_context, f"✅ Biblioteca de Estilos cargada ({len(files)} archivos)."
    except Exception as e:
        return None, f"Error leyendo JSONs: {e}"

# --- ESTADOS DE SESIÓN ---
if "refs_modelo" not in st.session_state:
    st.session_state.refs_modelo = []  # Identidad (Valeria)
if "refs_estilo" not in st.session_state:
    st.session_state.refs_estilo = []  # Pose / Iluminación
if "historial" not in st.session_state:
    st.session_state.historial = []
if "prompt_final" not in st.session_state:
    st.session_state.prompt_final = ""
if "json_data" not in st.session_state:
    data, msg = load_json_data()
    st.session_state.json_data = data
    st.session_state.json_msg = msg

# --- SEGURIDAD ---
try:
    # Intenta leer la clave real de los secretos locales/nube
    PASSWORD_ACCESO = st.secrets["PASSWORD_VALERIA"]
except Exception:
    # Si no existe el archivo secrets (ej. en GitHub público), usa una clave falsa
    # Esto protege tu contraseña real de ser vista en el código
    st.warning("⚠️ Configura 'PASSWORD_VALERIA' en .streamlit/secrets.toml")
    PASSWORD_ACCESO = "admin_dummy" 

def check_password():
    if "authenticated" not in st.session_state:
        st.title("Acceso Valeria AI")
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if pwd == PASSWORD_ACCESO:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrecta")
        return False
    return True

if check_password():
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

    # --- ENCABEZADO ---
    st.title("Valeria Desvelada AI Studio 💃")
    st.caption("Virtual Model Generation | Nano Banana Series")

    # --- GLOSARIO Y TUTORIAL ---
    with st.expander("📘 Guía de Comandos (PromptAssistantGEM - Edition Valeria)", expanded=False):
        st.markdown("""
        **Sistema de control para Modelo Virtual. Usa las mismas palabras clave que DeMos, adaptadas a fotografía de moda.**

        ### Flujo de Trabajo
        1.  **Carga Identidad (Izquierda):** Sube las fotos de la cara/cuerpo de Valeria. (Obligatorio para consistencia).
        2.  **Carga Estilo (Derecha):** Sube referencias de poses, luz o ropa (Opcional).
        3.  **Escribe Comando:** Ej: `Improve: Valeria en un café en París` o `Fashion Recipe: Editorial shot, vogue style`.

        ### Comandos Clave
        * **Improve:** Traduce una idea simple a un prompt fotográfico detallado usando tus JSONs.
        * **Fashion Recipe:** Estructura el prompt con: Sujeto + Outfit + Pose + Iluminación + Cámara + Estilo.
        * **Portrait Recipe:** Enfocado en primeros planos y detalles faciales.
        * **Describe:** Describe una imagen subida (útil para extraer estilos).
        """)
        
        if st.session_state.json_msg and "✅" in st.session_state.json_msg:
            st.success(st.session_state.json_msg)
        else:
            st.warning(st.session_state.json_msg or "Cargando JSONs...")

    st.divider()

    # --- CONTROLES SUPERIORES ---
    c_controls_1, c_controls_2 = st.columns([3, 1])
    with c_controls_1:
        modelo_nombre = st.selectbox("Motor de Render", [
            "Nano Banana Pro (Gemini 3 Pro Image)",
            "Nano Banana (Gemini 2.5 Flash Image)"
        ])
        model_map = {
            "Nano Banana Pro (Gemini 3 Pro Image)": "gemini-3-pro-image-preview",
            "Nano Banana (Gemini 2.5 Flash Image)": "gemini-2.5-flash-image"
        }
    with c_controls_2:
        st.write("") 
        st.write("") 
        if st.button("Recargar JSONs", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- ZONA 1: REFERENCIAS (DUAL) ---
    st.subheader("1. Referencias Visuales")
    
    col_identidad, col_estilo = st.columns(2)

    # COLUMNA 1: IDENTIDAD
    with col_identidad:
        st.markdown("##### 👤 Identidad (Valeria)")
        u_mod = st.file_uploader("Rasgos físicos (Cara/Cuerpo)", type=["jpg", "png"], key="u_mod", accept_multiple_files=True)
        if u_mod:
            for f in u_mod:
                if not any(d['name'] == f.name for d in st.session_state.refs_modelo):
                    st.session_state.refs_modelo.append({"img": PIL.Image.open(f), "name": f.name})
        
        # Galería Identidad
        if st.session_state.refs_modelo:
            c_m = st.columns(3)
            for i, ref in enumerate(st.session_state.refs_modelo):
                with c_m[i % 3]:
                    st.image(ref["img"], use_container_width=True)
                    if st.button("❌", key=f"del_m_{ref['name']}"):
                        st.session_state.refs_modelo.pop(i)
                        st.rerun()

    # COLUMNA 2: ESTILO
    with col_estilo:
        st.markdown("##### 🎨 Estilo / Pose / Outfit")
        u_sty = st.file_uploader("Poses, Iluminación, Ropa", type=["jpg", "png"], key="u_sty", accept_multiple_files=True)
        if u_sty:
            for f in u_sty:
                if not any(d['name'] == f.name for d in st.session_state.refs_estilo):
                    st.session_state.refs_estilo.append({"img": PIL.Image.open(f), "name": f.name})

        # Galería Estilo
        if st.session_state.refs_estilo:
            c_s = st.columns(3)
            for i, ref in enumerate(st.session_state.refs_estilo):
                with c_s[i % 3]:
                    st.image(ref["img"], use_container_width=True)
                    if st.button("❌", key=f"del_s_{ref['name']}"):
                        st.session_state.refs_estilo.pop(i)
                        st.rerun()

    st.divider()

    # --- ZONA 2: GENERADOR DE PROMPT (ULTIMATE ENGINE) ---
    st.subheader("2. Generador de Prompt (Valeria Engine)")
    
    st.markdown("**Instrucción Inicial**")
    cmd_input = st.text_area("Describe la escena (ej: 'Fashion Recipe: Valeria en alfombra roja, vestido gala')", height=100)
    
    if st.button("Mejorar Prompt", type="primary", use_container_width=True):
        if cmd_input:
            with st.spinner("Consultando JSONs de Estilo..."):
                try:
                    # Contexto JSON
                    json_context = json.dumps(st.session_state.json_data, indent=2, ensure_ascii=False) if st.session_state.json_data else "No JSON data."
                    
                    # Prompt del Sistema (Específico para Modelo Virtual)
                    system_prompt = f"""
                    You are 'PromptAssistantGEM', specialized in Virtual Model Photography (Valeria Desvelada).
                    I have loaded a library of styles/lighting in JSON:
                    {json_context}

                    YOUR RULES:
                    1. 'Improve:': Create a photorealistic fashion/portrait prompt using the JSON terms.
                    2. 'Fashion Recipe': Structure -> Subject (Valeria) + Outfit Details + Pose + Environment + Lighting + Camera Specs.
                    3. ALWAYS maintain the subject name as 'Valeria Desvelada' in the prompt to trigger identity consistency.
                    4. Use the JSON files to fill in specific details about lighting (e.g., 'Butterfly lighting') or camera (e.g., '85mm lens').
                    
                    TASK: Output ONLY the final optimized prompt text.
                    USER COMMAND: {cmd_input}
                    """
                    
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=system_prompt
                    )
                    
                    if res.text:
                        texto_limpio = res.text.strip()
                        st.session_state.prompt_final = texto_limpio
                        st.session_state["fp_valeria"] = texto_limpio # Forzar actualización widget
                        st.rerun()
                    else:
                        st.error("Respuesta vacía del asistente.")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Escribe una instrucción.")

    st.markdown("**Prompt Final (Editable)**")
    
    if "prompt_final" not in st.session_state:
        st.session_state.prompt_final = ""

    final_prompt = st.text_area("Resultado optimizado:", 
                              value=st.session_state.prompt_final, 
                              height=150, 
                              key="fp_valeria")
    
    if final_prompt != st.session_state.prompt_final:
        st.session_state.prompt_final = final_prompt

    # --- ZONA 3: GENERACIÓN ---
    st.divider()
    
    if st.button("Generar a Valeria ✨", use_container_width=True):
        if st.session_state.prompt_final:
            if not st.session_state.refs_modelo:
                st.warning("⚠️ Cuidado: No has subido referencias de Identidad. Valeria podría no parecerse a sí misma.")
            
            with st.status("Renderizando a Valeria...", expanded=False) as status:
                try:
                    # Construcción del Prompt Maestro Multimodal
                    # 1. Instrucción de Texto
                    master_instruction = f"""
                    Generate a photorealistic image of the model 'Valeria Desvelada'.
                    CRITICAL IDENTITY INSTRUCTION: Use the FIRST group of images provided (Identity References) to replicate her face and body features exactly.
                    STYLE INSTRUCTION: Use the SECOND group of images (if any) only for pose, lighting, and composition.
                    SCENE DESCRIPTION: {st.session_state.prompt_final}
                    """
                    
                    # 2. Lista de Contenidos: [Texto, Refs Modelo..., Refs Estilo...]
                    contenido_solicitud = [master_instruction]
                    
                    # Extraer solo los objetos PIL Image de los diccionarios
                    imgs_modelo = [item["img"] for item in st.session_state.refs_modelo]
                    imgs_estilo = [item["img"] for item in st.session_state.refs_estilo]
                    
                    contenido_solicitud.extend(imgs_modelo)
                    contenido_solicitud.extend(imgs_estilo)
                    
                    # 3. Llamada API
                    response = client.models.generate_content(
                        model=model_map[modelo_nombre],
                        contents=contenido_solicitud,
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"]
                        )
                    )
                    
                    if response and response.parts:
                        img_result = None
                        for part in response.parts:
                            if part.inline_data:
                                img_result = PIL.Image.open(BytesIO(part.inline_data.data))
                                break
                        
                        if img_result:
                            st.session_state.historial.insert(0, img_result)
                            if len(st.session_state.historial) > 10:
                                st.session_state.historial.pop()
                            status.update(label="¡Valeria generada!", state="complete")
                            st.rerun()
                        else:
                            st.error("Bloqueo de seguridad o error de generación.")
                    else:
                        st.error("Error API.")
                        
                except Exception as e:
                    st.error(f"Error crítico: {e}")
        else:
            st.warning("El prompt está vacío.")

    # --- HISTORIAL ---
    if st.session_state.historial:
        st.divider()
        st.subheader("Historial de Sesión")
        
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.historial):
            with cols[i % 3]:
                st.image(img, use_container_width=True)
                
                c1, c2, c3 = st.columns([1, 1, 1])
                
                # Descargar Original
                buf = BytesIO()
                img.save(buf, format="PNG")
                c1.download_button("💾", buf.getvalue(), f"valeria_{i}.png", "image/png", key=f"dl_{i}")
                
                # 4K Upscale
                if c2.button("🔍 4K", key=f"up_{i}"):
                    with st.spinner("Reescalando..."):
                        img_4k = upscale_image(img)
                        buf_4k = BytesIO()
                        img_4k.save(buf_4k, format="PNG", optimize=True)
                        st.session_state[f"ready_4k_val_{i}"] = buf_4k.getvalue()
                        st.rerun()
                
                if f"ready_4k_val_{i}" in st.session_state:
                    c2.download_button("⬇️", st.session_state[f"ready_4k_val_{i}"], f"valeria_4k_{i}.png", "image/png", key=f"dl4k_{i}")

                # Usar como Referencia (Se manda a ESTILO para no corromper la identidad)
                if c3.button("🔄 Ref", key=f"ref_{i}", help="Usar como referencia de Estilo/Pose"):
                    st.session_state.refs_estilo.append({
                        "img": img,
                        "name": f"gen_valeria_{int(time.time())}.png"
                    })
                    st.toast("Añadida a Referencias de Estilo", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
