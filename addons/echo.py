description = "echoes back the input text"
args = {
    "text": {
        "type": "string",
		}
}
required = ["text"]

def main(text):
    return f"echo: {text}"