import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Speech to Text

Use this to loadbalance across Azure + OpenAI. 

## Quick Start

```python
from llm import transcription
import os 

# set api keys 
os.environ["OPENAI_API_KEY"] = ""
audio_file = open("/path/to/audio.mp3", "rb")

response = transcription(model="whisper", file=audio_file)

print(f"response: {response}")
```

## Proxy Usage

### Add model to config 


<Tabs>
<TabItem value="openai" label="OpenAI">

```yaml
model_list:
- model_name: whisper
  llm_params:
    model: whisper-1
    api_key: os.environ/OPENAI_API_KEY
  model_info:
    mode: audio_transcription
    
general_settings:
  master_key: sk-1234
```
</TabItem>
<TabItem value="openai+azure" label="OpenAI + Azure">

```yaml
model_list:
- model_name: whisper
  llm_params:
    model: whisper-1
    api_key: os.environ/OPENAI_API_KEY
  model_info:
    mode: audio_transcription
- model_name: whisper
  llm_params:
    model: azure/azure-whisper
    api_version: 2024-02-15-preview
    api_base: os.environ/AZURE_EUROPE_API_BASE
    api_key: os.environ/AZURE_EUROPE_API_KEY
  model_info:
    mode: audio_transcription

general_settings:
  master_key: sk-1234
```

</TabItem>
</Tabs>

### Start proxy 

```bash
llm --config /path/to/config.yaml 

# RUNNING on http://0.0.0.0:8000
```

### Test 

<Tabs>
<TabItem value="curl" label="Curl">

```bash
curl --location 'http://0.0.0.0:8000/v1/audio/transcriptions' \
--header 'Authorization: Bearer sk-1234' \
--form 'file=@"/Users/zeekay/Downloads/gettysburg.wav"' \
--form 'model="whisper"'
```

</TabItem>
<TabItem value="openai" label="OpenAI">

```python
from openai import OpenAI
client = openai.OpenAI(
    api_key="sk-1234",
    base_url="http://0.0.0.0:8000"
)


audio_file = open("speech.mp3", "rb")
transcript = client.audio.transcriptions.create(
  model="whisper",
  file=audio_file
)
```
</TabItem>
</Tabs>

## Supported Providers

- OpenAI
- Azure
- [Fireworks AI](./providers/fireworks_ai.md#audio-transcription)
- [Groq](./providers/groq.md#speech-to-text---whisper)
- [Deepgram](./providers/deepgram.md)