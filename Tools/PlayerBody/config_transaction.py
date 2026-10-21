"""Scoped writes to player_body.json; no UE, Git, or gameplay side effects.

Call commit(path, original_bytes, candidate, owned_paths=[("clips", role), ...],
            producer=__file__). Candidate may be a dict, UTF-8 bytes, or text.
"""
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid


class ConfigConflict(RuntimeError):
    pass


_MISSING = object()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigConflict("Duplicate JSON key: " + key)
        result[key] = value
    return result


def _load(value):
    if isinstance(value, bytes):
        value = value.decode("utf-8-sig")
    return json.loads(value, object_pairs_hook=_unique)


def _changes(before, after, path=()):
    if before is _MISSING and isinstance(after, dict) and after:
        for key, value in after.items():
            yield from _changes(_MISSING, value, path + (key,))
    elif isinstance(before, dict) and not isinstance(after, dict):
        raise ConfigConflict("Replacing an object would implicitly remove its keys: " + repr(path))
    elif isinstance(before, dict) and isinstance(after, dict):
        for key in dict.fromkeys([*before, *after]):
            yield from _changes(before.get(key, _MISSING), after.get(key, _MISSING), path + (key,))
    elif type(before) is not type(after) or before != after:
        yield path, after


def _span(text, path):
    decoder = json.JSONDecoder()

    def ws(pos):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos

    start = ws(0)
    for key in path:
        if text[start] != "{":
            raise ConfigConflict("Expected JSON object at " + repr(path))
        pos = ws(start + 1)
        while text[pos] != "}":
            name, end = decoder.raw_decode(text, pos)
            pos = ws(ws(end) + 1)
            _, end = decoder.raw_decode(text, pos)
            if name == key:
                start = pos
                break
            pos = ws(end)
            if text[pos] == ",":
                pos = ws(pos + 1)
        else:
            raise KeyError(path)
    _, end = decoder.raw_decode(text, start)
    return start, end


def _set(text, path, value):
    newline = "\r\n" if "\r\n" in text else "\n"
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    try:
        start, end = _span(text, path)
    except KeyError:
        try:
            start, end = _span(text, path[:-1])
        except KeyError:
            # Ownership was checked at each new leaf; create only its missing parents.
            return _set(_set(text, path[:-1], {}), path, value)
        line = text[text.rfind("\n", 0, start) + 1:start]
        indent = len(line) - len(line.lstrip()) + 2
        obj = json.loads(text[start:end])
        insertion = end - 1
        while insertion > start + 1 and text[insertion - 1].isspace():
            insertion -= 1
        payload = encoded.replace("\n", newline + " " * indent)
        entry = (" " * indent) + json.dumps(path[-1], ensure_ascii=False) + ": " + payload
        addition = ("," if obj else "") + newline + entry
        if insertion == end - 1:
            addition += newline + " " * max(0, indent - 2)
        return text[:insertion] + addition + text[insertion:]
    line = text[text.rfind("\n", 0, start) + 1:start]
    indent = len(line) - len(line.lstrip())
    return text[:start] + encoded.replace("\n", newline + " " * indent) + text[end:]


@contextlib.contextmanager
def _lock(path):
    # OS releases this lock on exit/crash; the persistent file is not a stale lock.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ConfigConflict("Another config writer is active; retry from fresh input.") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ConfigConflict("Another config writer is active; retry from fresh input.") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def commit(path, before, candidate, *, owned_paths, producer):
    path = Path(path).resolve()
    if path.name != "player_body.json" or path.parent.name != "ColdSteelData" or path.parent.parent.name != "Content":
        raise ValueError("This writer is only for Content/ColdSteelData/player_body.json")
    if not isinstance(before, bytes):
        raise TypeError("Capture original bytes before preparing any edits")
    scopes = [tuple(p) for p in owned_paths]
    if any(not p or p == ("clips",) for p in scopes):
        raise ConfigConflict("Declare individual clip roles; whole-document/whole-clips ownership is forbidden")
    original = _load(before)
    proposed = _load(json.dumps(candidate, ensure_ascii=False, allow_nan=False)) if isinstance(candidate, dict) else _load(candidate)
    edits = list(_changes(original, proposed))
    for key, value in edits:
        if value is _MISSING:
            raise ConfigConflict("Implicit key removal is forbidden: " + repr(key))
        if not any(key[:len(scope)] == scope for scope in scopes):
            raise ConfigConflict("Change outside declared ownership: " + repr(key))
    text = before.decode("utf-8-sig")
    for key, value in edits:
        text = _set(text, key, value)
    result = (b"\xef\xbb\xbf" if before.startswith(b"\xef\xbb\xbf") else b"") + text.encode("utf-8")
    if _load(result) != proposed:
        raise ConfigConflict("Scoped result differs from proposed configuration")
    root = path.parents[2]
    saved = root / "Saved/PlayerBodyConfigWrites"
    with _lock(saved / "writer.lock"):
        if path.read_bytes() != before:
            raise ConfigConflict("Configuration changed after read; discard candidate and merge from fresh input.")
        if not edits:
            return {"status": "unchanged", "local_config_applied": True, "git_commit": None, "git_push": None}
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        folder = saved / (stamp + "-" + uuid.uuid4().hex[:8])
        folder.mkdir()
        (folder / "before.json").write_bytes(before)
        (folder / "after.json").write_bytes(result)
        report = {
            "status": "prepared", "producer": str(producer), "config": str(path),
            "owned_paths": scopes, "changed_paths": [k for k, _ in edits],
            "before_sha256": hashlib.sha256(before).hexdigest(),
            "after_sha256": hashlib.sha256(result).hexdigest(),
            "local_config_applied": False, "git_commit": None, "git_push": None,
            "runtime_tested": False, "receipt": str(folder / "receipt.json"),
        }
        receipt = folder / "receipt.json"
        receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".player-body-", suffix=".tmp", delete=False) as stream:
                temp_path = Path(stream.name)
                stream.write(result)
                stream.flush()
                os.fsync(stream.fileno())
            if path.read_bytes() != before:
                raise ConfigConflict("An unmanaged writer changed the configuration; preserving its bytes.")
            os.replace(temp_path, path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
        report.update(status="applied", local_config_applied=True)
        receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
