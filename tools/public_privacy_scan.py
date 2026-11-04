#!/usr/bin/env python3
"""Public-source privacy lint: redacted output only. Not a substitute for history review."""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile, BadZipFile
ROOT=Path(__file__).resolve().parents[1]
SENSITIVE_EXT={'.md','.csv','.json','.jsonl','.txt','.xml','.html','.css','.js','.mjs','.ts','.tsx','.py','.ps1','.psm1','.psd1','.sql','.yml','.yaml','.toml','.svg','.sh','.log','.ini','.cmd','.bat','.ipynb','.xlsx'}
IGNORE={'tools/public_privacy_scan.py','tests/public_data_modes.test.mjs'}
EMAIL=re.compile(r'\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b',re.I)
WIN=re.compile(r'C:\\Users\\([^\\\s"\'\x60<>]+)',re.I)
UNIX=re.compile(r'(?<![A-Za-z0-9./])/(?:home|Users)/([a-z0-9._-]{3,})/',re.I)
TOKEN=re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{30})\b')
PRIVATE_KEY=re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----')
DENY_DOMAINS={'gmail.com','outlook.com','hotmail.com','icloud.com','yahoo.com','protonmail.com','aol.com'}
SAFE_SUFFIXES=('.example','.invalid','.test','.internal')
SAFE_WIN_USERS={'public','default','sampleuser','exampleuser','username','user','testuser','yourname'}
SAFE_UNIX_USERS={'runner','ubuntu','example','username','user','testuser','root'}
def classify(text):
    flags=set()
    if TOKEN.search(text): flags.add('possible credential token')
    if PRIVATE_KEY.search(text):flags.add('private-key block')
    for m in EMAIL.finditer(text):
        domain=m.group(1).lower()
        if domain in DENY_DOMAINS:flags.add('personal email address')
        elif not domain.endswith(SAFE_SUFFIXES) and domain not in {'example.com','example.org','example.net'}:
            flags.add('non-example email domain')
    for m in WIN.finditer(text):
        if m.group(1).lower() not in SAFE_WIN_USERS:flags.add('specific Windows profile path')
    for m in UNIX.finditer(text):
        if m.group(1).lower() not in SAFE_UNIX_USERS:flags.add('specific Unix profile path')
    return sorted(flags)
def paths():
    try:
        result=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT)
        return [ROOT / strpath.decode('utf-8') for strpath in result.split(b'\0') if strpath]
    except (OSError,subprocess.CalledProcessError):
        return [p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts]
def run():
    checked=0; issues=[]
    for path in paths():
        rel=path.relative_to(ROOT).as_posix()
        if rel in IGNORE or path.suffix.lower() not in SENSITIVE_EXT or not path.is_file():continue
        if path.stat().st_size>3_000_000:issues.append((rel,['oversized file requires separate review']));continue
        if path.suffix.lower()=='.xlsx':
            try:
                with ZipFile(path) as archive:
                    text='\n'.join(archive.read(n).decode('utf-8','replace') for n in archive.namelist() if n.endswith('.xml') or n.endswith('.rels'))
            except (OSError,BadZipFile):issues.append((rel,['unreadable Excel workbook']));continue
        else:
            text=path.read_text(encoding='utf-8',errors='replace')
        checked+=1
        flags=classify(text)
        if flags:issues.append((rel,flags))
    print(f'Checked {checked} tracked text / workbook files. Potential issues: {len(issues)}.')
    for path,flags in issues:
        print(f'  {path}: '+', '.join(flags)) # Never print matched values.
    return 1 if issues else 0
if __name__=='__main__':sys.exit(run())
