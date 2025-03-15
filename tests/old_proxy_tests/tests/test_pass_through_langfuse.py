from langfuse import Langfuse

langfuse = Langfuse(
    host="http://localhost:4000",
    public_key="anything",
    secret_key="anything",
)

print("sending langfuse trace request")
trace = langfuse.trace(name="test-trace-llm-proxy-passthrough")
print("flushing langfuse request")
langfuse.flush()

print("flushed langfuse request")
