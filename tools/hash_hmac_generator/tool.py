#!/usr/bin/env python3
import hashlib
import hmac
from typing import Any, Dict

def compute_hash(text: str, algorithm: str = "sha256", key: str = "") -> Dict[str, Any]:
    algo = algorithm.lower().strip()
    data_bytes = text.encode("utf-8")
    
    if key:
        key_bytes = key.encode("utf-8")
        if algo == "sha256":
            digest = hmac.new(key_bytes, data_bytes, hashlib.sha256).hexdigest()
        elif algo == "sha512":
            digest = hmac.new(key_bytes, data_bytes, hashlib.sha512).hexdigest()
        elif algo == "sha1":
            digest = hmac.new(key_bytes, data_bytes, hashlib.sha1).hexdigest()
        elif algo == "md5":
            digest = hmac.new(key_bytes, data_bytes, hashlib.md5).hexdigest()
        else:
            return {"status": "error", "error": f"Unsupported algorithm: {algorithm}"}
        return {"status": "success", "mode": "hmac", "algorithm": algo, "digest": digest, "length": len(digest)}
    
    if algo == "sha256":
        digest = hashlib.sha256(data_bytes).hexdigest()
    elif algo == "sha512":
        digest = hashlib.sha512(data_bytes).hexdigest()
    elif algo == "sha1":
        digest = hashlib.sha1(data_bytes).hexdigest()
    elif algo == "md5":
        digest = hashlib.md5(data_bytes).hexdigest()
    else:
        return {"status": "error", "error": f"Unsupported algorithm: {algorithm}"}
        
    return {"status": "success", "mode": "hash", "algorithm": algo, "digest": digest, "length": len(digest)}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    text = params.get("text", "")
    algorithm = params.get("algorithm", "sha256")
    key = params.get("key", "")
    return compute_hash(text, algorithm, key)
