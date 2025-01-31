import streamlit as st
import pdfplumber
import pytesseract
from PIL import Image
import pandas as pd
import re
import unicodedata
from PyPDF2 import PdfReader
import matplotlib.pyplot as plt

# Configuração do Tesseract (se necessário para OCR)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Ajuste para Linux no Streamlit Cloud

def normalizar_texto(texto):
    """Remove acentos e converte para minúsculas."""
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto.lower().strip()

def fix_spacing(text):
    """Corrige a falta de espaços no texto extraído do PDF."""
    fixed_text = re.sub(r'(?<=[a-záéíóúç])(?=[A-ZÁÉÍÓÚÇ])', ' ', text)
    return fixed_text

def extrair_texto_pdf(pdf_file):
    """Extrai e corrige o texto de PDFs baseados em texto."""
    text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    # Caso não haja texto extraível, aplicar OCR na imagem da página
                    img = page.to_image(resolution=300).original
                    img = img.convert("L")  # Converte para escala de cinza para melhor OCR
                    text += pytesseract.image_to_string(img)
    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")

    return fix_spacing(text)

def extrair_nomes_pdf(pdf_file):
    """Extrai nomes completos do PDF, normalizando-os."""
    text = extrair_texto_pdf(pdf_file)
    matches = re.findall(r'\b[A-ZÀ-Ú][A-ZÀ-Úa-zà-ú]+\s[A-ZÀ-Úa-zà-ú ]+\b', text)
    return sorted({normalizar_texto(name) for name in matches})

def check_names_in_pdf(pdf_file, names):
    """Verifica quais nomes da lista estão no PDF."""
    found_names = []
    approved_names = extrair_nomes_pdf(pdf_file)

    # Depuração: Exibir nomes extraídos e buscados
    print("\n🔍 Nomes extraídos do PDF:", approved_names)
    print("🔎 Nomes buscados:", names)

    for name in names:
        normalized_name = normalizar_texto(name)
        if normalized_name in approved_names:
            found_names.append(name)

    return found_names

def main(names, pdf_files):
    results = []
    for pdf_file in pdf_files:
        found_names = check_names_in_pdf(pdf_file, names)
        if found_names:
            for name in found_names:
                results.append({"Nome": name, "PDF": pdf_file.name})

    # Depuração: Exibir os resultados encontrados no terminal
    print("Resultados encontrados:", results)

    # Criando DataFrame
    df = pd.DataFrame(results)

    # Verifica se há nomes antes de ordenar
    if not df.empty and "Nome" in df.columns:
        df = df.drop_duplicates()
        df = df.sort_values(by="Nome").reset_index(drop=True)  # Ordena apenas se a coluna existir
        df.insert(0, "Nº", range(1, len(df) + 1))  # Adiciona numeração iniciando em 1
    else:
        st.error("Erro: Nenhum nome foi encontrado nos PDFs. Verifique os arquivos e a lista de nomes.")

    return df

def gerar_graficos(resultados_df, total_nomes):
    """Gera gráficos para análise dos resultados."""
    if resultados_df.empty:
        st.warning("Nenhum dado para gerar gráficos.")
        return

    # Gráfico de Barras: Quantidade de alunos encontrados por PDF
    pdf_counts = resultados_df["PDF"].value_counts()
    fig_bar, ax_bar = plt.subplots(figsize=(8, 5))
    pdf_counts.plot(kind="bar", ax=ax_bar, color="skyblue", edgecolor="black")
    ax_bar.set_title("Quantidade de Alunos Encontrados por PDF")
    ax_bar.set_xlabel("Arquivo PDF")
    ax_bar.set_ylabel("Número de Alunos")
    plt.xticks(rotation=45)
    st.pyplot(fig_bar)

    # Gráfico de Pizza: Percentual de alunos encontrados
    alunos_encontrados = len(resultados_df)
    alunos_nao_encontrados = total_nomes - alunos_encontrados
    alunos_nao_encontrados = max(0, alunos_nao_encontrados)  # Evita valores negativos

    fig_pie, ax_pie = plt.subplots(figsize=(6, 6))
    ax_pie.pie(
        [alunos_encontrados, alunos_nao_encontrados],
        labels=["Encontrados", "Não Encontrados"],
        autopct="%1.1f%%",
        colors=["#4CAF50", "#FF5733"],
        startangle=90,
    )
    ax_pie.set_title("Percentual de Alunos Encontrados")
    st.pyplot(fig_pie)

# Interface do Streamlit
st.title("Encontra aluno(s). Versão 1.6 - Agora com Depuração 🔍📊 - análise de pdf via OCR")

st.write("Faça upload de um arquivo CSV com os nomes dos alunos ou cole manualmente.")

# Upload do CSV com a lista de nomes
csv_file = st.file_uploader("📂 Faça upload de um arquivo CSV com os nomes", type="csv")

# Se um CSV for carregado, extrair os nomes dele
if csv_file:
    df_nomes = pd.read_csv(csv_file, header=None)  # Lê o CSV sem cabeçalho
    names = df_nomes[0].dropna().astype(str).str.strip().tolist()
    st.success(f"{len(names)} nomes carregados do CSV!")
else:
    names_input = st.text_area("Ou cole a lista de nomes (um por linha):")
    names = [name.strip() for name in names_input.split("\n") if name.strip()]

# Upload de PDFs
pdf_files = st.file_uploader("📂 Faça upload dos PDFs", type="pdf", accept_multiple_files=True)

# Depuração: Mostrar arquivos carregados
if pdf_files:
    st.write("📂 Arquivos carregados:")
    for pdf in pdf_files:
        st.write(f"- {pdf.name}")  # Exibe os nomes dos PDFs carregados

if st.button("🔍 Analisar PDFs"):
    if not pdf_files:
        st.warning("⚠ Nenhum PDF foi carregado! Verifique se o upload foi bem-sucedido.")
    elif not names:
        st.warning("⚠ Nenhum nome foi inserido! Faça upload de um CSV ou digite os nomes manualmente.")
    else:
        with st.spinner("Analisando PDFs... ⏳"):
            resultados = main(names, pdf_files)
            if resultados.empty:
                st.write("Nenhum nome foi encontrado nos PDFs.")
            else:
                st.write("📋 **Resultados: Alunos encontrados**")
                st.dataframe(resultados)

                # Download CSV
                csv = resultados.to_csv(index=False).encode("utf-8")
                st.download_button("⬇ Baixar resultados em CSV", data=csv, file_name="resultados.csv", mime="text/csv")

                # Gerar gráficos após exibir os resultados
                gerar_graficos(resultados, len(names))
