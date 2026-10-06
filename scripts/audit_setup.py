"""Read-only setup inventory comparison. Never prints config values or credentials."""
import json
import hashlib
from pathlib import Path
import tomllib


def collect(home):
    cfg = tomllib.loads((home / '.codex/config.toml').read_text())
    skill_root = home / '.agents/skills'
    skills = []
    if skill_root.exists():
        for folder in sorted(skill_root.iterdir()):
            if not folder.is_dir():
                continue
            for path in sorted(folder.rglob('SKILL.md')):
                content = path.read_bytes()
                skills.append({'path': str(path.relative_to(skill_root)), 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
    return {
        'preferences': {k: cfg[k] for k in ('model', 'model_reasoning_effort', 'personality', 'service_tier') if k in cfg},
        'project_entry_count': len(cfg.get('projects', {})),
        'mcp_names': sorted(cfg.get('mcp_servers', {})),
        'provider_count': len(cfg.get('model_providers', {})),
        'explicit_plugins': {k: v.get('enabled') if isinstance(v, dict) else None for k, v in cfg.get('plugins', {}).items()},
        'user_skills': skills,
    }


def main():
    root = Path(__file__).resolve().parents[1]
    now = collect(Path.home())
    original = root / 'instructions/AGENTS.md'
    applied = Path.home() / '.codex/AGENTS.md'
    skill_root = Path.home() / '.agents/skills'
    from apply_managed import render, targets
    same = applied.exists() and render(original, Path.home()) == applied.read_bytes()
    from install_core_skills import snapshot
    core_copies = {}
    for source in (root / 'skills').iterdir():
        if not (source / 'SKILL.md').is_file():
            continue
        target = skill_root / source.name
        core_copies[source.name] = target.is_dir() and not target.is_symlink() and snapshot(target) == snapshot(source)
    result = {
        'read_only': True,
        'core_skill_copies': core_copies,
        'global_instructions': 'same_contents' if same else 'different_not_applied',
        'observed_counts': {'mcp': len(now['mcp_names']), 'providers': now['provider_count'], 'user_skill_files': len(now['user_skills']), 'explicit_plugins': len(now['explicit_plugins'])},
        'evidence_level': 'file_comparison_only_not_runtime_validation',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
