#!/usr/bin/env python3
import argparse
import hashlib
import json
from hereticbench.client import OpenAICompatClient

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base-url",default="http://127.0.0.1:8080/v1")
    p.add_argument("--timeout",type=int,default=30)
    a=p.parse_args()
    c=OpenAICompatClient(a.base_url,timeout=a.timeout)
    print(json.dumps(c.models(),indent=2))
    try:
        props=c.props()
        tmpl=props.get("chat_template") or ""
        print("server_model_path="+str(props.get("model_path")))
        print("server_build_info="+str(props.get("build_info")))
        print("chat_template_sha256="+(hashlib.sha256(tmpl.encode("utf-8")).hexdigest() if tmpl else "unknown"))
        print("chat_template_chars="+str(len(tmpl)))
        print("chat_template_caps="+json.dumps(props.get("chat_template_caps") or {},sort_keys=True))
        try:
            rendered=(c.apply_template([{"role":"user","content":"HERETICBENCH_TEMPLATE_FINGERPRINT_V1"}]).get("prompt") or "")
            print("effective_template_probe_sha256="+(hashlib.sha256(rendered.encode("utf-8")).hexdigest() if rendered else "unknown"))
        except Exception as e:
            print("effective_template_probe_error="+repr(e))
    except Exception as e:
        print("props_error="+repr(e))

if __name__=="__main__":
    main()
