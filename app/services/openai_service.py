from openai import OpenAI
import shelve
from dotenv import load_dotenv
import os
import time
import logging

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
client = OpenAI(api_key=OPENAI_API_KEY)


assistant = client.beta.assistants.create(
  name="WhatsApp DocMovi Asistente",
  instructions="Eres una asistente virtual que ayuda a los usuarios de docmovi a entender el funcionamiento de la empresa, los servicios, planes, precios y todo lo relacionado. Actua de forma amable y convincente. Responde solo a preguntas que tengan que ver con DocMovi y de las que extraigas la informacion del documento que se te proporcionó como data. Cuando hagan preguntas que no tengan que ver con DocMovi y sus servicios o data responde amablemente que no estas autorizado a responder sobre otros temas.",
  model="gpt-4o-mini",
  tools=[{"type": "file_search"}],
)



# --------------------------------------------------------------
# Upload file
# --------------------------------------------------------------
# def upload_file(path):
#     # Upload a file with an "assistants" purpose
#     file = client.files.create(file=open(path, "rb"), purpose="assistants")
#     return file


# file = upload_file("data/airbnb-faq.pdf")

# Create a vector store caled "Financial Statements"
vector_store = client.beta.vector_stores.create(name="DocMoviData")
 
# Ready the files for upload to OpenAI
file_paths = ["leocisternasa/python_chatbot/data/DocMovi_Data.pdf"]
file_streams = [open(path, "rb") for path in file_paths]
 
# Use the upload and poll SDK helper to upload the files, add them to the vector store,
# and poll the status of the file batch for completion.
file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
  vector_store_id=vector_store.id, files=file_streams
)
 
# You can print the status and the file counts of the batch to see the result of this operation.
print(file_batch.status)
print(file_batch.file_counts)

##Upload the assistant created
assistant = client.beta.assistants.update(
  assistant_id=assistant.id,
  tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)



# --------------------------------------------------------------
# Create assistant
# --------------------------------------------------------------
# def create_assistant(file):
#     """
#     You currently cannot set the temperature for Assistant via the API.
#     """
#     assistant = client.beta.assistants.create(
#         name="WhatsApp AirBnb Assistant",
#         instructions="You're a helpful WhatsApp assistant that can assist guests that are staying in our Paris AirBnb. Use your knowledge base to best respond to customer queries. If you don't know the answer, say simply that you cannot help with question and advice to contact the host directly. Be friendly and funny.",
#         tools=[{"type": "file_search"}],
#         model="gpt-4-1106-preview",
#         file_ids=[file.id],
#     )
#     return assistant


# assistant = create_assistant(file)


# --------------------------------------------------------------
# Thread management
# --------------------------------------------------------------
def check_if_thread_exists(wa_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)


def store_thread(wa_id, thread_id):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id


# --------------------------------------------------------------
# Generate response
# --------------------------------------------------------------
def generate_response(message_body, wa_id, name):
    thread_id = check_if_thread_exists(wa_id)

    if thread_id is None:
        print(f"Creating new thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.create()
        store_thread(wa_id, thread.id)
        thread_id = thread.id
    else:
        print(f"Retrieving existing thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.retrieve(thread_id)

    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_body,
    )

    new_message = run_assistant(thread)
    if new_message:
        print(f"To {name}: {new_message}")
    else:
        print(f"To {name}: No se pudo generar una respuesta.")
    return new_message
# --------------------------------------------------------------
# Run assistant
# --------------------------------------------------------------
def run_assistant(thread):
    try:
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )

        # Poll for completion
        while run.status not in ['completed', 'failed']:
            time.sleep(1)  # Wait for 1 second before checking again
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        if run.status == 'failed':
            print(f"Run failed: {run.last_error}")
            return "Lo siento, hubo un error al procesar tu solicitud."

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        if messages.data:
            new_message = messages.data[0].content[0].text.value
            print(f"Generated message: {new_message}")
            return new_message
        else:
            return "No se generó ninguna respuesta."

    except Exception as e:
        print(f"Error in run_assistant: {str(e)}")
        return "Ocurrió un error inesperado."
    # Retrieve the Assistant
    # assistant = client.beta.assistants.retrieve(assistant.id)

    # Run the assistant
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    # Wait for completion
    if run.status == 'completed':
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )
        print(messages)
        new_message = messages.data[0].content[0].text.value
        print(f"Generated message: {new_message}")
        return new_message
    else:
        print(run.status)
        return None  
