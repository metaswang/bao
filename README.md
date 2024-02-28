# BobGPT

BobGPT is an AI project that allows you to ask questions about youtube videos.

![Gradio Web UI](/gradio-ui.png)

> In the case, the target youtube video is [Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE) from Andrej Karpathy.

# How it works?
![RAG Diagram](rag-framework.png)

# Install & Run
Before running below cmd, make sure you have figured out the settings in settings.yaml based on your real scenarios.
```
# validated on python 3.11+
# senarios
# create vitual env 
python3 -m venv .venv
source venv/bin/activate
pip install -Urq requirements.txt

python -m bao
```