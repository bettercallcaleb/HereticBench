#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

TEMPLATE = """{% for message in messages %}<|im_start|>{{ message['role'] }}\n{{ message['content'] }}<|im_end|>\n{% endfor %}<|im_start|>assistant\n"""

class H(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass

    def sendj(self,obj):
        b=json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.endswith("/models"):
            self.sendj({"object":"list","data":[{"id":"mock-model","object":"model"}]})
        elif self.path == "/props":
            self.sendj({
                "model_path":"mock-model-Q4_K_M.gguf",
                "chat_template":TEMPLATE,
                "chat_template_caps":{"supports_system_role":True},
                "build_info":"mock-b1"
            })
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        n=int(self.headers.get("Content-Length","0"))
        body=json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/apply-template":
            msgs=body.get("messages") or []
            prompt="".join(f"<|im_start|>{m.get('role')}\n{m.get('content')}<|im_end|>\n" for m in msgs)+"<|im_start|>assistant\n"
            self.sendj({"prompt":prompt})
            return
        if not self.path.endswith("/chat/completions"):
            self.send_response(404)
            self.end_headers()
            return
        prompt=(body.get("messages") or [{}])[-1].get("content","")
        content="HB_OK" if "HB_OK" in prompt else "This is a mock answer."
        reasoning="" if body.get("reasoning_effort")=="none" else "mock reasoning"
        self.sendj({
            "id":"mock",
            "object":"chat.completion",
            "model":"mock-model",
            "choices":[{
                "index":0,
                "message":{"role":"assistant","content":content,"reasoning_content":reasoning},
                "finish_reason":"stop"
            }],
            "usage":{"prompt_tokens":17,"completion_tokens":5,"total_tokens":22},
            "timings":{"predicted_n":5,"predicted_ms":10.0,"predicted_per_second":500.0}
        })

if __name__=="__main__":
    HTTPServer(("127.0.0.1",18080),H).serve_forever()
