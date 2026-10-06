"""Verify real GAM semantic retrieval in a disposable Vault and daemon."""
import argparse, asyncio, json, secrets, socket, subprocess, tempfile, tomllib, uuid
from pathlib import Path
from probe_tools import connect, call, require
from setup_runtime import state_root, write_json

def memory_id(value):
    if isinstance(value, dict):
        ident = value.get('id')
        if isinstance(ident, str) and ident.startswith('mem_'):
            return ident
        for item in value.values():
            found = memory_id(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = memory_id(item)
            if found:
                return found
    return None

async def probe(tools):
    with tempfile.TemporaryDirectory(prefix='gam-semantic-') as directory:
        root = Path(directory)
        vault, data, token = root/'vault', root/'state', root/'token'
        token.write_text(secrets.token_urlsafe(48))
        token.chmod(0o600)
        with socket.socket() as probe_socket:
            probe_socket.bind(('127.0.0.1', 0))
            port = probe_socket.getsockname()[1]
        daemon = str(Path(tools['gam']).with_name('global-memoryd'))
        config = tomllib.loads(Path(tools['gam_config']).read_text())
        model = config['embeddings']['model']
        command = [daemon, '--vault', str(vault), '--state', str(data), '--token-file', str(token),
                   '--port', str(port), '--embedding-provider', 'ollama',
                   '--embedding-model', model, '--no-watch']
        log_path = root/'daemon.log'
        with log_path.open('w') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(50):
                    if process.poll() is not None:
                        raise RuntimeError('GAM daemon exited before readiness: '+log_path.read_text()[-1000:])
                    try:
                        with socket.create_connection(('127.0.0.1', port), timeout=.1):
                            break
                    except OSError:
                        await asyncio.sleep(.1)
                else:
                    raise RuntimeError('GAM daemon was not ready')
                endpoint = f'http://127.0.0.1:{port}/mcp'
                async with connect(tools['gam_mcp'], ['--endpoint', endpoint, '--token-file', str(token)]) as session:
                    project = 'semantic-fixture'
                    await call(session, 'memory_projects', {'action': 'add', 'request_id': str(uuid.uuid4()),
                        'payload': {'name': project, 'roots': [str(root/'repo')]}})
                    candidate = await call(session, 'memory_remember', {
                        'request_id': str(uuid.uuid4()), 'title': 'Vehicle emergency',
                        'content': 'The automobile tire lost all pressure while driving; replace the damaged wheel before continuing.',
                        'type': 'fact', 'scope': 'project', 'project': project, 'force': True})
                    ident = memory_id(candidate)
                    require(ident, 'GAM did not return a memory ID')
                    await call(session, 'memory_approve', {'id': ident, 'request_id': str(uuid.uuid4())})
                    for _ in range(30):
                        status = (await call(session, 'memory_status', {}))['data']
                        result = (await call(session, 'memory_search', {
                            'query': 'roadside puncture', 'project': project, 'mode': 'semantic'}))['data']
                        match = next((item for item in result['results'] if item['memory_id'] == ident), None)
                        if match and match.get('semantic_rank'):
                            require(status['embedding_state'] == 'configured', 'Embeddings not configured')
                            require(status['vector_state'] == 'available', 'Vector index unavailable')
                            require(result['mode_used'] == 'semantic', 'Search did not use semantic mode')
                            return {'gam_semantic': True, 'semantic_rank': match['semantic_rank'],
                                    'mode_used': result['mode_used'], 'isolated_vault': True}
                        await asyncio.sleep(.5)
                    raise RuntimeError('GAM semantic retrieval did not return the approved fixture')
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, default=state_root())
    args = parser.parse_args()
    tools = json.loads((args.state/'tools.json').read_text())
    result = asyncio.run(probe(tools))
    write_json(args.state/'receipts/gam-semantic-probe.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
