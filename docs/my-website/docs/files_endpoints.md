
import TabItem from '@theme/TabItem';
import Tabs from '@theme/Tabs';

# /files

Files are used to upload documents that can be used with features like Assistants, Fine-tuning, and Batch API.

## Quick Start

- Upload a File
- List Files
- Retrieve File Information
- Delete File
- Get File Content

<Tabs>
<TabItem value="proxy" label="LLM PROXY Server">

```bash
$ export OPENAI_API_KEY="sk-..."

$ llm

# RUNNING on http://0.0.0.0:4000
```

**Upload a File**
```bash
curl http://localhost:4000/v1/files \
  -H "Authorization: Bearer sk-1234" \
  -F purpose="fine-tune" \
  -F file="@mydata.jsonl"
```

**List Files**
```bash
curl http://localhost:4000/v1/files \
  -H "Authorization: Bearer sk-1234"
```

**Retrieve File Information**
```bash
curl http://localhost:4000/v1/files/file-abc123 \
  -H "Authorization: Bearer sk-1234"
```

**Delete File**
```bash
curl http://localhost:4000/v1/files/file-abc123 \
  -X DELETE \
  -H "Authorization: Bearer sk-1234"
```

**Get File Content**
```bash
curl http://localhost:4000/v1/files/file-abc123/content \
  -H "Authorization: Bearer sk-1234"
```

</TabItem>
<TabItem value="sdk" label="SDK">

**Upload a File**
```python
from llm
import os 

os.environ["OPENAI_API_KEY"] = "sk-.."

file_obj = await llm.acreate_file(
    file=open("mydata.jsonl", "rb"),
    purpose="fine-tune",
    custom_llm_provider="openai",
)
print("Response from creating file=", file_obj)
```

**List Files**
```python
files = await llm.alist_files(
    custom_llm_provider="openai",
    limit=10
)
print("files=", files)
```

**Retrieve File Information**
```python
file = await llm.aretrieve_file(
    file_id="file-abc123",
    custom_llm_provider="openai"
)
print("file=", file)
```

**Delete File**
```python
response = await llm.adelete_file(
    file_id="file-abc123",
    custom_llm_provider="openai"
)
print("delete response=", response)
```

**Get File Content**
```python
content = await llm.afile_content(
    file_id="file-abc123",
    custom_llm_provider="openai"
)
print("file content=", content)
```

</TabItem>
</Tabs>


## **Supported Providers**:

### [OpenAI](#quick-start)

## [Azure OpenAI](./providers/azure#azure-batches-api)

### [Vertex AI](./providers/vertex#batch-apis)

## [Swagger API Reference](https://llm-api.up.railway.app/#/files)
