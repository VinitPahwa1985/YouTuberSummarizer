import yt_dlp as youtube_dl
import requests
import pytube
import re
import gradio as gr
from langchain_community.document_loaders import YoutubeLoader
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.llms import Ollama
import tiktoken

def get_youtube_description(url: str):
    try:
        full_html = requests.get(url).text
        y = re.search(r'shortDescription":"', full_html)
        desc = ""
        count = y.start() + 19  # adding the length of the 'shortDescription":"
        while True:
            letter = full_html[count]
            if letter == "\"":
                if full_html[count - 1] == "\\":
                    desc += letter
                    count += 1
                else:
                    break
            else:
                desc += letter
                count += 1
        return desc
    except Exception as e:
        return f"Error: {e}"

def get_youtube_info(url: str):
    try:
        ydl_opts = {
        'format': 'best',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',  # Convert to mp4 format
        }],
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get('title', 'None')
            desc = info_dict.get('description', 'None')
        return title, desc
    except Exception as e:
        return "Error", f"Error: {e}"

def get_text_splitter(chunk_size: int, overlap_size: int):
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=chunk_size, chunk_overlap=overlap_size)

def wrap_docs_to_string(docs):
    return " ".join([doc.page_content for doc in docs]).strip()

def get_youtube_transcript_loader_langchain(url):
    # This is a placeholder for the actual LangChain YouTube loader function
    # Replace this with the actual implementation
    from langchain.document_loaders import YoutubeLoader
    loader = YoutubeLoader.from_youtube_url(url)
    return loader.load()

def get_youtube_transcription(url: str):
    try:
        # Load the transcript using LangChain's YouTube loader
        docs = get_youtube_transcript_loader_langchain(url)
        
        # Combine the document contents into a single string
        text = wrap_docs_to_string(docs)
        
        # Encode the text using the tiktoken encoder for the GPT-4 model
        enc = tiktoken.encoding_for_model("gpt-4")
        count = len(enc.encode(text))
        
        return text, count
    except Exception as e:
        # Return an error message and a count of 0 in case of an exception
        return f"Error: {e}", 0
    
def get_transcription_summary(url: str, temperature: float, chunk_size: int, overlap_size: int):
    try:
        docs = get_youtube_transcript_loader_langchain(url)
        text_splitter = get_text_splitter(chunk_size=chunk_size, overlap_size=overlap_size)
        split_docs = text_splitter.split_documents(docs)
        llm = Ollama(
        model="llama3.2:1b",
        base_url="http://localhost:11434",
        temperature=temperature,
        )
        chain = load_summarize_chain(llm, chain_type="map_reduce")
        output = chain.invoke(split_docs)
        return output['output_text']
    except Exception as e:
        return f"Error: {e}"

with gr.Blocks() as demo:
    gr.Markdown("# YouTube Summarizer with Llama 3")
    with gr.Row(equal_height=True):
        with gr.Column(scale=4):
            url = gr.Textbox(label='YouTube URL', value="https://youtu.be/bvPDQ4-0LAQ")
        with gr.Column(scale=1):
            bttn_info_get = gr.Button('Get Info', variant='primary')
            bttn_clear = gr.ClearButton(interactive=True, variant='stop')
            
    with gr.Row(variant='panel'):
        with gr.Column(scale=2):
            title = gr.Textbox(label='Title', lines=2, max_lines=10, show_copy_button=True)
        with gr.Column(scale=3):
            desc = gr.Textbox(label='Description', max_lines=10, autoscroll=False, show_copy_button=True)
            bttn_info_get.click(fn=get_youtube_info, inputs=url, outputs=[title, desc], api_name="get_youtube_info")

    with gr.Row(equal_height=True):        
        with gr.Column():
            bttn_trns_get = gr.Button("Get Transcription", variant='primary')
            tkncount = gr.Number(label='Token Count (est)')
        with gr.Column():
            bttn_summ_get = gr.Button("Summarize", variant='primary')
            with gr.Row():
                with gr.Column(scale=1, min_width=100):
                    temperature = gr.Number(label='Temperature', minimum=0.0, step=0.01, precision=-2)
                with gr.Column(scale=1, min_width=100):
                    chunk = gr.Number(label='Chunk Size', minimum=200, step=100, value=4000)
                with gr.Column(scale=1, min_width=100):
                    overlap = gr.Number(label='Overlap Size', minimum=0, step=10, value=0)
        
    with gr.Row():
        with gr.Column():
            trns_raw = gr.Textbox(label='Transcript', show_copy_button=True)
        with gr.Column():
            trns_sum = gr.Textbox(label="Summary", show_copy_button=True)
    
    bttn_trns_get.click(fn=get_youtube_transcription, inputs=url, outputs=[trns_raw, tkncount])
    bttn_summ_get.click(fn=get_transcription_summary, inputs=[url, temperature, chunk, overlap], outputs=trns_sum)
    bttn_clear.add([url, title, desc, trns_raw, trns_sum, tkncount])

if __name__ == "__main__":
    demo.launch(share=True)
