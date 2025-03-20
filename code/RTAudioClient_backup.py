# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import asyncio
import os
import json

import numpy as np
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from scipy.signal import resample
import streamlit as st
from Utilities import Utilities
from openai import AzureOpenAI 
import pyaudio


import wave
import io
from rtclient import (
    InputAudioTranscription,
    RTAudioContent,
    RTClient,
    RTInputAudioItem,
    RTMessageItem,
    RTResponse,
    NoTurnDetection,
)
from RAGHandler import RAGHandler
st.set_page_config(
    layout="wide",
    page_title="GraphRAG-powered AI Assistant",
    page_icon="🧠",
    menu_items={
        'About': "This is an app that uses GraphRAG to answer questions when necessary using the GPT-4o realtime audio API."
    }
)
st.title("GraphRAG-powered AI Assistant")
def run_UI():
    
    with st.sidebar:
        #global_or_local = st.selectbox("Use local or global search?",["Local","Global"])
        local = True
        #if global_or_local == "Global":
            #local = False
            #st.session_state["search_mode"] = local
        show_history = st.checkbox("Show History", value=False, on_change=set_no_play)
        st.session_state["search_mode"] = local
        st.write("Model Family: GPT-4")
        st.write("Model: GPT-4o")
        st.session_state["frame_rate"] = st.slider("Audio Frequency (Hz)",min_value=16000,max_value=48000,step=1000, value =25000)
        if st.button("Stop Playback"):
            if st.session_state["playing"]:
                # Signal the thread to stop
                st.session_state["stop_playback_flag"] = True
                st.session_state["played_audio"] = True
                # The thread itself will set st.session_state["playing"] = False once it ends
            else:
                st.write("No audio is currently playing.")
        if "playing" not in st.session_state:
            st.session_state["playing"] = False
        if "stop_playback_flag" not in st.session_state:
            st.session_state["stop_playback_flag"] = False
        if "playback_thread" not in st.session_state:
            st.session_state["playback_thread"] = None
        if "played_audio" not in st.session_state:
            st.session_state["played_audio"] = False
        if "processing" not in st.session_state:
            st.session_state["processing"] = st.empty()
    audio_file = st.audio_input("Ask GPT a question by clicking the microphone icon, then click the stop icon to send it to GPT.",on_change=reset_audio)
    if not "messages" in st.session_state:
            st.session_state["messages"] = []
    messages = st.session_state["messages"]
    if show_history:
        for message in messages:
            with st.chat_message(message['role']):
                st.markdown(message['content'])
    if audio_file is not None and not st.session_state["played_audio"]:
    # To read file as bytes:
        bytes_data = audio_file.getvalue()
        asyncio.run(with_azure_openai(bytes_data))
def set_no_play():
    st.session_state["played_audio"] = True
def reset_audio():
    st.session_state["played_audio"] = False
def resample_audio(audio_data, original_sample_rate, target_sample_rate):
    number_of_samples = round(len(audio_data) * float(target_sample_rate) / original_sample_rate)
    resampled_audio = resample(audio_data, number_of_samples)
    return resampled_audio.astype(np.int16)


async def send_audio(client: RTClient, audio_bytes: bytes):
   
    await client.send_audio(audio_bytes)


async def receive_message_item(item: RTMessageItem):
    prefix = f"[response={item.response_id}][item={item.id}]"
    async for contentPart in item:
        if contentPart.type == "audio":

            async def collect_audio(audioContentPart: RTAudioContent):
                audio_data = bytearray()
                async for chunk in audioContentPart.audio_chunks():
                    audio_data.extend(chunk)
                return audio_data

            async def collect_transcript(audioContentPart: RTAudioContent):
                audio_transcript: str = ""
                async for chunk in audioContentPart.transcript_chunks():
                    audio_transcript += chunk
                return audio_transcript

            audio_task = asyncio.create_task(collect_audio(contentPart))
            transcript_task = asyncio.create_task(collect_transcript(contentPart))
            audio_data, audio_transcript = await asyncio.gather(audio_task, transcript_task)
            print(prefix, f"Audio received with length: {len(audio_data)}")
            print(prefix, f"Audio Transcript: {audio_transcript}")
            response_message = {
                "role":"Assistant",
                "content": audio_transcript
            }
            st.session_state["messages"].append(response_message)
            st.session_state["processing"].empty()
            st.write(audio_transcript)
            # Parameters for your PCM data (example values)
            num_channels = 1
            sample_width = 2  # 16-bit
            frame_rate =  st.session_state["frame_rate"]
            # Create a WAV file in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(num_channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(frame_rate)
                wav_file.writeframes(audio_data)

            # Get the complete .wav file bytes
            wav_bytes = wav_buffer.getvalue()
            play_wav_bytes(wav_bytes)
            # Now Streamlit can play it
            #st.audio(wav_bytes, format='audio/wav')

def play_wav_bytes(wav_bytes):
    try:
        st.session_state["played_audio"] = False
        st.session_state["playing"] = True
        st.session_state["stop_playback_flag"] = False

        with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
            p = pyaudio.PyAudio()
            
            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )

            chunk_size = 1024
            data = wf.readframes(chunk_size)
            
            while data and not st.session_state["stop_playback_flag"]:
                stream.write(data)
                data = wf.readframes(chunk_size)
            st.session_state["playing"] = False
            # Cleanup
            stream.stop_stream()
            stream.close()
            p.terminate()
            st.session_state["played_audio"] = True
    except st.runtime.scriptrunner.script_runner.StopException:
    # StopException is how Streamlit forcibly interrupts the script.
    # We can handle any final cleanup here:
    # For example, close resources if not already closed.
        pass
async def receive_response(client: RTClient, response: RTResponse):
    prefix = f"[response={response.id}]"
    async for item in response:
        print(prefix, f"Received item {item.id}")
        print(item.type)
        if item.type == "message":
            asyncio.create_task(receive_message_item(item))
        elif item.type == "function_call":
            asyncio.create_task(call_function(client, item))

    print(prefix, f"Response completed ({response.status})")
    if response.status == "completed":
        await client.close()


async def receive_input_item(item: RTInputAudioItem):

    prefix = f"[input_item={item.id}]"
    await item
    print(prefix, f"Transcript: {item.transcript}")
    print(prefix, f"Audio Start [ms]: {item.audio_start_ms}")
    print(prefix, f"Audio End [ms]: {item.audio_end_ms}")


async def receive_events(client: RTClient):
    async for event in client.events():
        print(event.type)
        if event.type == "input_audio":
            asyncio.create_task(receive_input_item(event))
        elif event.type == "response":
            asyncio.create_task(receive_response(client, event))

async def call_function(client, item):
    await item
    function_name = item.function_name  
    arguments = json.loads(item.arguments)
    function_to_call = client.available_functions[function_name]
    # invoke the function with the arguments and get the response
    response = function_to_call(**arguments)
    response_message = {
        "role":"Assistant",
        "content":response,
    }
    st.session_state["messages"].append(response_message)
    st.markdown(response)
    #handle_question(arguments,st.session_state["model"],response, "")

    
async def receive_messages(client: RTClient):
    await asyncio.gather(
        receive_events(client),
    )


async def run(client: RTClient, audio_data: bytes):
    print("Configuring Session...", end="", flush=True)
    tools_list = [
    {
        "type": "function",
        "name": "search_function",
        "description": "This is a search function you can use to provide an overview of the documents or to answer a specific question the user asks about diseases, drugs, or outcomes. ",
        "parameters": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description" : "The search term to be used to search for information"
                }
            },
            "required": ["search_term"],
        },
    }
    ]



    client.available_functions = {"search_function": search_function}

    await client.configure(
            instructions="You are a helpful AI that can provide information on diseases, drugs, and outcomes. You can also answer questions related to drugs, diseases, or outcomes using the search function you have access to.",
            turn_detection=NoTurnDetection(),
            input_audio_transcription=InputAudioTranscription(model="whisper-1"),
            tools=tools_list,
            tool_choice="auto"
        )
    print("Done")

    await send_audio(client, audio_data)

    input_item = await client.commit_audio()
    response = await client.generate_response()
    st.session_state["processing"] = st.info("Thinking...")
    await asyncio.gather(
        receive_response(client, response),
        receive_input_item(input_item),
    )
    st.session_state["processing"].empty()
    
def search_function(search_term: str):
        search_term = search_term+" Be sure to include any relevant context information in your search term such as drug names. The questions will always relate to Nivolumab."
        results_parsed = ""
        st.session_state["processing"].empty()
        with st.status(f"Searching for content using GraphRAG..."):
            search_result = ""
            if st.session_state["search_mode"]:
                search_result = st.session_state["RAGQuery_object"].local_search(search_term,2)
            else:
                search_result = st.session_state["RAGQuery_object"].global_search(search_term,1)
            results_parsed = RAGHandler.parse_query_response(search_result, return_context_data=False)
            #print(results_parsed)
        st.success("Search complete!")
        return "GraphRAG Search Result: " + results_parsed
    
def get_env_var(var_name: str) -> str:
    value = os.environ.get(var_name)
    if not value:
        raise OSError(f"Environment variable '{var_name}' is not set or is empty.")
    return value


async def with_azure_openai(audio_data: bytes):
    endpoint = get_env_var("AZURE_OPENAI_ENDPOINT")
    key = get_env_var("AZURE_OPENAI_API_KEY")
    deployment = get_env_var("AZURE_OPENAI_DEPLOYMENT")
    async with RTClient(url=endpoint, key_credential=AzureKeyCredential(key), azure_deployment=deployment) as client:
        await run(client, audio_data)
def init_clients(openai_api_version,endpoint,openai_key,aoai_model):
    client = AzureOpenAI(
        azure_endpoint = endpoint, 
        api_key=openai_key,  
        api_version=openai_api_version
    )
    
    st.session_state["AOAI_client"] = client
    st.session_state["model"] = aoai_model
def init_RAG_query(graphrag_config):
    graphrag_endpoint = graphrag_config["endpoint"]
    graphrag_key = graphrag_config["key"]
    graphrag_index_name = graphrag_config["index_name"]
    graphrag_storage_name = graphrag_config["storage_name"]
    print(graphrag_index_name)
    print(graphrag_storage_name)
    RAGQuery_object = RAGHandler(key=graphrag_key,endpoint=graphrag_endpoint,
                                 storage_name=graphrag_storage_name,index_name=graphrag_index_name)
    return RAGQuery_object
if __name__ == "__main__":
    env_path = r"C:\Users\dade\Desktop\GraphRagAPI\.env"
    load_dotenv(env_path,override=True)
    app_config_data = Utilities.read_json_data(get_env_var("APP_CONFIG"))
    print(app_config_data["graphrag_config_path"])
    graphrag_config = Utilities.read_json_data(app_config_data["graphrag_config_path"])
    openai_config_data = Utilities.read_json_data(app_config_data["aoai_config_path"])
    init_clients(openai_config_data["api_version"],
                 openai_config_data["endpoint"],
                 openai_config_data["key"],
                 openai_config_data["model"])
    RAGQuery_object = init_RAG_query(graphrag_config)
    st.session_state["RAGQuery_object"] = RAGQuery_object
    run_UI()
   

