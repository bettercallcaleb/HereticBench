import json
import time
import urllib.error
import urllib.request

class OpenAICompatClient:
    def __init__(self, base_url, timeout=600):
        self.base_url = base_url.rstrip("/")
        self.root_url = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
        self.timeout = timeout

    def _request_url(self, method, url, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            payload = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code} from {url}: {payload}") from e

    def _request(self, method, path, body=None):
        return self._request_url(method, self.base_url + path, body)

    def _request_root(self, method, path, body=None):
        return self._request_url(method, self.root_url + path, body)

    def models(self):
        return self._request("GET", "/models")

    def props(self):
        return self._request_root("GET", "/props")

    def apply_template(self, messages):
        return self._request_root("POST", "/apply-template", {"messages": messages})

    def chat(self, messages, model=None, max_tokens=1024, temperature=0.0, reasoning_effort="medium"):
        body = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if model:
            body["model"] = model
        if reasoning_effort not in (None, "", "default", "native"):
            body["reasoning_effort"] = reasoning_effort
        if reasoning_effort == "none":
            body["chat_template_kwargs"] = {"enable_thinking": False}
        started = time.perf_counter()
        data = self._request("POST", "/chat/completions", body)
        elapsed = time.perf_counter() - started
        msg = data["choices"][0]["message"]
        usage = data.get("usage") or {}
        return {
            "content": msg.get("content") or "",
            "reasoning_content": msg.get("reasoning_content") or "",
            "usage": usage,
            "timings": data.get("timings") or {},
            "model": data.get("model") or model,
            "elapsed_seconds": elapsed,
            "raw_finish_reason": data["choices"][0].get("finish_reason"),
        }
