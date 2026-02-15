import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
from io import BytesIO

# Configuración de página
st.set_page_config(page_title="Valeria Desvelada AI Studio", layout="wide", page_icon="💃")

# --- ESTADOS DE SESIÓN ---
if "refs_modelo" not in st.session_state:
    st.session_state.refs_modelo = [] 
if "refs_estilo" not in st.session_state:
    st.session_state.refs_estilo = [] 

if "historial" not in st.session_state:
    st.session_state.historial = []

# --- SEGURIDAD ---
PASSWORD_ACCESO = "valeria2026"

def check_password():
    if "authenticated" not in st.session_state:
        st.sidebar.title("Acceso Privado")
        pwd = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Entrar"):
            if pwd == PASSWORD_ACCESO:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.sidebar.error("Contraseña incorrecta")
        return False
    return True

if check_password():
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

    st.title("Valeria Desvelada AI Studio 💃")
    st.caption("Generación de modelo virtual | Nano Banana Series")

    # --- SIDEBAR: CONFIGURACIÓN ---
    with st.sidebar:
        st.header("Ajustes de Generación")
        modelo_nombre = st.selectbox("Motor de Render", [
            "Nano Banana Pro (Gemini 3 Pro Image)",
            "Nano Banana (Gemini 2.5 Flash Image)"
        ])
        
        model_map = {
            "Nano Banana Pro (Gemini 3 Pro Image)": "gemini-3-pro-preview", 
            "Nano Banana (Gemini 2.5 Flash Image)": "gemini-2.5-flash-image"
        }
        
        # Selección de formato (se enviará como texto en el prompt)
        aspect_ratio = st.selectbox("Formato (Aspect Ratio)", 
                                   ["2:3", "9:16", "1:1", "16:9", "3:2", "4:5", "5:4"])

    # --- SECCIÓN 1: IDENTIDAD DE LA MODELO (VALERIA) ---
    st.subheader("1. Identidad de Valeria (Obligatorio)")
    st.caption("Sube aquí imágenes que definan su rostro, cuerpo y outfits específicos.")
    
    uploaded_modelo = st.file_uploader("Arrastra referencias de IDENTIDAD aquí", 
                                     type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="upload_modelo")
    
    if uploaded_modelo:
        for f in uploaded_modelo:
            img = PIL.Image.open(f)
            if not any(d['name'] == f.name for d in st.session_state.refs_modelo):
                st.session_state.refs_modelo.append({"img": img, "name": f.name})

    # Galería Modelo
    refs_modelo_activas = []
    if st.session_state.refs_modelo:
        cols_m = st.columns(6)
        for i, ref in enumerate(st.session_state.refs_modelo):
            with cols_m[i % 6]:
                st.image(ref["img"], use_container_width=True)
                if st.checkbox(f"Usar Identidad", value=True, key=f"check_mod_{ref['name']}"):
                    refs_modelo_activas.append(ref["img"])
        if st.button("Limpiar Identidad", key="clean_mod"):
            st.session_state.refs_modelo = []
            st.rerun()

    st.divider()

    # --- SECCIÓN 2: REFERENCIAS DE ESTILO Y POSE ---
    st.subheader("2. Referencias de Estilo y Pose (Opcional)")
    st.caption("Sube imágenes para copiar iluminación, composición o posturas.")
    
    uploaded_estilo = st.file_uploader("Arrastra referencias de ESTILO aquí", 
                                     type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="upload_estilo")
    
    if uploaded_estilo:
        for f in uploaded_estilo:
            img = PIL.Image.open(f)
            if not any(d['name'] == f.name for d in st.session_state.refs_estilo):
                st.session_state.refs_estilo.append({"img": img, "name": f.name})

    # Galería Estilo
    refs_estilo_activas = []
    if st.session_state.refs_estilo:
        cols_e = st.columns(6)
        for i, ref in enumerate(st.session_state.refs_estilo):
            with cols_e[i % 6]:
                st.image(ref["img"], use_container_width=True)
                if st.checkbox(f"Usar Estilo", key=f"check_est_{ref['name']}"):
                    refs_estilo_activas.append(ref["img"])
        if st.button("Limpiar Estilos", key="clean_est"):
            st.session_state.refs_estilo = []
            st.rerun()

    # --- ÁREA DE PROMPT Y GENERACIÓN ---
    st.divider()
    st.subheader("Descripción de la Escena")
    prompt_usuario = st.text_area("Detalla el entorno, la acción y la ropa:", 
                                  placeholder="Ej: Valeria está sentada en un café parisino...")

    if st.button("Generar a Valeria ✨"):
        if prompt_usuario and refs_modelo_activas:
            with st.status("Procesando a Valeria...", expanded=False) as status:
                try:
                    st.write("Configurando prompt...")
                    
                    # 1. Prompt Maestro con Aspect Ratio incrustado en texto
                    instrucciones_base = """
                    Genera una imagen de la modelo virtual "Valeria Desvelada".
                    INSTRUCCIONES DE IDENTIDAD:
                    1. Replica EXÁCTAMENTE las características faciales y corporales del primer grupo de imágenes (Identidad).
                    INSTRUCCIONES DE ESTILO:
                    2. Usa el segundo grupo de imágenes (si existen) solo para pose e iluminación.
                    """
                    
                    # Aquí inyectamos el aspect ratio como texto
                    prompt_final_texto = f"{instrucciones_base}\n\nPARAMETROS TÉCNICOS:\nFormato de imagen: {aspect_ratio}\n\nDESCRIPCIÓN DE ESCENA:\n{prompt_usuario}"

                    # 2. Combinación de recursos
                    contenido_solicitud = [prompt_final_texto] + refs_modelo_activas + refs_estilo_activas

                    # 3. Llamada al modelo (Sin aspect_ratio en config)
                    st.write(f"Renderizando con {modelo_nombre}...")
                    response = client.models.generate_content(
                        model=model_map[modelo_nombre],
                        contents=contenido_solicitud,
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"]
                        )
                    )

                    # Validación
                    if response and response.parts:
                        resultado = None
                        for part in response.parts:
                            if part.inline_data:
                                resultado = PIL.Image.open(BytesIO(part.inline_data.data))
                                break
                        
                        if resultado:
                            st.session_state.historial.insert(0, resultado)
                            if len(st.session_state.historial) > 10:
                                st.session_state.historial.pop()

                            st.subheader("Resultado Final")
                            st.image(resultado, use_container_width=True, caption=f"Valeria Desvelada | Formato {aspect_ratio}")
                            status.update(label="Generación exitosa", state="complete")
                        else:
                            st.error("El modelo no devolvió una imagen válida.")
                    else:
                        st.error("La API no devolvió contenido.")

                except Exception as e:
                    st.error(f"Error crítico: {e}")
        elif not refs_modelo_activas:
             st.warning("⚠️ Sube al menos una imagen de IDENTIDAD.")
        else:
            st.warning("Escribe una descripción.")

    # --- HISTORIAL ---
    if st.session_state.historial:
        st.divider()
        st.subheader("Historial de Sesión")
        h_cols = st.columns(5)
        for i, h_img in enumerate(st.session_state.historial):
            with h_cols[i % 5]:
                st.image(h_img, use_container_width=True)
                buf = BytesIO()
                h_img.save(buf, format="PNG")
                st.download_button(f"Guardar", buf.getvalue(), f"valeria_{i}.png", "image/png", key=f"dl_{i}")
