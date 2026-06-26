#!/usr/bin/env python3
import http.server
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

PORT = 8767
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
STATE_FILE = DATA_DIR / 'state.json'
CONFIG_FILE = DATA_DIR / 'config.json'


def ensure_data():
    DATA_DIR.mkdir(exist_ok=True)
    if not STATE_FILE.exists():
        STATE_FILE.write_text(json.dumps({"tracks": []}))
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps({"githubToken": "", "workflowDocUrl": ""}))


def parse_pr_url(url):
    parsed = urllib.parse.urlparse(url)
    parts = [p for p in parsed.path.split('/') if p]
    if len(parts) < 4 or parts[2] != 'pull':
        raise ValueError("Invalid PR URL — expected github.com/owner/repo/pull/number")
    return parts[0], parts[1], parts[3]


def github_graphql(query, token):
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Merginator/1.0',
        'Content-Type': 'application/json',
    }
    if token:
        headers['Authorization'] = f'bearer {token}'
    try:
        req = urllib.request.Request(
            'https://api.github.com/graphql',
            data=json.dumps({'query': query}).encode(),
            headers=headers,
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'_err': e.code, '_msg': e.reason}
    except Exception as e:
        return {'_err': 0, '_msg': str(e)}


def github(path, token, method='GET', data=None):
    url = f'https://api.github.com{path}'
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Merginator/1.0',
    }
    if token:
        headers['Authorization'] = f'token {token}'
    if data:
        headers['Content-Type'] = 'application/json'
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode() if data else None,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'_err': e.code, '_msg': e.reason}
    except Exception as e:
        return {'_err': 0, '_msg': str(e)}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        path = p.path
        params = urllib.parse.parse_qs(p.query)

        if path in ('/', '/index.html'):
            self._file('merginator.html', 'text/html')
        elif path == '/api/state':
            self._json(json.loads(STATE_FILE.read_text()))
        elif path == '/api/config':
            config = json.loads(CONFIG_FILE.read_text())
            safe = {k: v for k, v in config.items() if k != 'githubToken'}
            safe['hasToken'] = bool(config.get('githubToken', ''))
            self._json(safe)
        elif path == '/api/github/pr':
            self._pr_fetch(params)
        elif path == '/api/github/detect':
            self._detect(params)
        elif path == '/api/github/ci':
            self._ci_status(params)
        elif path == '/api/github/gate':
            self._gate_check(params)
        else:
            self._json({'error': 'Not found'}, 404)

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except (ValueError, json.JSONDecodeError):
            return self._json({'error': 'Invalid request body'}, 400)
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/state':
            STATE_FILE.write_text(json.dumps(body, indent=2))
            self._json({'ok': True})
        elif path == '/api/config':
            existing = json.loads(CONFIG_FILE.read_text())
            if not body.get('githubToken'):
                body['githubToken'] = existing.get('githubToken', '')
            CONFIG_FILE.write_text(json.dumps(body, indent=2))
            self._json({'ok': True})
        elif path == '/api/github/comment':
            self._post_comment(body)
        else:
            self._json({'error': 'Not found'}, 404)

    def _pr_fetch(self, params):
        url = params.get('url', [''])[0]
        if not url:
            return self._json({'error': 'No URL'}, 400)
        try:
            owner, repo, number = parse_pr_url(url)
        except ValueError as e:
            return self._json({'error': str(e)}, 400)
        token = json.loads(CONFIG_FILE.read_text()).get('githubToken', '')
        pr = github(f'/repos/{owner}/{repo}/pulls/{number}', token)
        if '_err' in pr:
            return self._json({'error': pr['_msg']}, 400)
        self._json({
            'title': pr.get('title', ''),
            'number': pr.get('number'),
            'repo': f'{owner}/{repo}',
            'state': pr.get('state'),
            'draft': pr.get('draft', False),
            'requestedTeams': [t.get('name', '') for t in pr.get('requested_teams', [])],
        })

    def _detect(self, params):
        url = params.get('url', [''])[0]
        if not url:
            return self._json({'error': 'No URL'}, 400)
        try:
            owner, repo, number = parse_pr_url(url)
        except ValueError as e:
            return self._json({'error': str(e)}, 400)

        token = json.loads(CONFIG_FILE.read_text()).get('githubToken', '')
        comments = github(f'/repos/{owner}/{repo}/issues/{number}/comments?per_page=100', token)
        reviews = github(f'/repos/{owner}/{repo}/pulls/{number}/reviews', token)
        reviewers = github(f'/repos/{owner}/{repo}/pulls/{number}/requested_reviewers', token)

        step = 2
        notes = []

        # Step 2 done: Claude bot has commented
        claude_commented = False
        if isinstance(comments, list):
            for c in comments:
                login = c.get('user', {}).get('login', '').lower()
                body_text = c.get('body', '').lower()
                if (login in ('claude[bot]', 'claude-ai[bot]', 'anthropic-claude[bot]') or
                        (login.endswith('[bot]') and
                         all(kw in body_text for kw in ('performance', 'security', 'correctness')))):
                    claude_commented = True
                    break

        if claude_commented:
            step = 3
            # Step 3 done: no pending CHANGES_REQUESTED
            if isinstance(reviews, list):
                pending = [r for r in reviews if r.get('state') == 'CHANGES_REQUESTED']
                if not pending:
                    step = 4
                    notes.append(
                        "Steps 4 (update PR description) and 5 (Linear evidence) "
                        "cannot be detected automatically — verify these are done."
                    )

        # Step 6+: reviewer has been requested or has interacted
        has_activity = isinstance(reviews, list) and len(reviews) > 0
        has_requested = isinstance(reviewers, dict) and (
            len(reviewers.get('users', [])) > 0 or len(reviewers.get('teams', [])) > 0
        )
        if has_activity or has_requested:
            step = max(step, 6)
            if isinstance(reviews, list):
                if any(r.get('state') in ('CHANGES_REQUESTED', 'COMMENTED') for r in reviews):
                    step = max(step, 7)
                if any(r.get('state') == 'APPROVED' for r in reviews):
                    step = max(step, 8)

        self._json({'step': step, 'notes': notes})

    def _ci_status(self, params):
        url = params.get('url', [''])[0]
        if not url:
            return self._json({'error': 'No URL'}, 400)
        try:
            owner, repo, number = parse_pr_url(url)
        except ValueError as e:
            return self._json({'error': str(e)}, 400)
        token = json.loads(CONFIG_FILE.read_text()).get('githubToken', '')
        pr = github(f'/repos/{owner}/{repo}/pulls/{number}', token)
        if '_err' in pr:
            return self._json({'error': pr['_msg']}, 400)
        sha = pr.get('head', {}).get('sha', '')
        if not sha:
            return self._json({'error': 'Could not get head SHA'}, 400)
        runs = github(f'/repos/{owner}/{repo}/commits/{sha}/check-runs?per_page=100', token)
        if '_err' in runs:
            return self._json({'error': runs['_msg']}, 400)
        items = runs.get('check_runs', [])
        if not items:
            return self._json({'status': 'pending', 'summary': 'No checks found yet'})
        pending = [r for r in items if r.get('status') != 'completed']
        failed  = [r for r in items if r.get('status') == 'completed' and
                   r.get('conclusion') not in ('success', 'neutral', 'skipped')]
        if pending:
            return self._json({'status': 'pending', 'summary': f'{len(pending)} check(s) still running'})
        if failed:
            names = ', '.join(r.get('name','?') for r in failed[:3])
            return self._json({'status': 'failing', 'summary': f'Still failing: {names}'})
        return self._json({'status': 'passing', 'summary': f'All {len(items)} checks passed'})

    def _gate_check(self, params):
        url = params.get('url', [''])[0]
        if not url:
            return self._json({'error': 'No URL'}, 400)
        try:
            owner, repo, number = parse_pr_url(url)
        except ValueError as e:
            return self._json({'error': str(e)}, 400)
        token = json.loads(CONFIG_FILE.read_text()).get('githubToken', '')

        # CI status
        pr = github(f'/repos/{owner}/{repo}/pulls/{number}', token)
        if '_err' in pr:
            return self._json({'error': pr['_msg']}, 400)

        if pr.get('merged'):
            return self._json({
                'merged': True,
                'ci': {'status': 'passing', 'summary': 'PR already merged'},
                'conversations': {'resolved': True, 'unresolved': 0},
            })

        sha = pr.get('head', {}).get('sha', '')
        ci = {'status': 'unknown', 'summary': 'Could not fetch CI status'}
        if sha:
            runs = github(f'/repos/{owner}/{repo}/commits/{sha}/check-runs?per_page=100', token)
            if '_err' not in runs:
                items = runs.get('check_runs', [])
                if not items:
                    ci = {'status': 'pending', 'summary': 'No checks found yet'}
                else:
                    pending = [r for r in items if r.get('status') != 'completed']
                    failed  = [r for r in items if r.get('status') == 'completed' and
                               r.get('conclusion') not in ('success', 'neutral', 'skipped')]
                    if pending:
                        ci = {'status': 'pending', 'summary': f'{len(pending)} check(s) still running'}
                    elif failed:
                        names = ', '.join(r.get('name', '?') for r in failed[:3])
                        ci = {'status': 'failing', 'summary': f'Failing: {names}'}
                    else:
                        ci = {'status': 'passing', 'summary': f'All {len(items)} checks passed'}

        # Unresolved review threads via GraphQL
        query = '''{
  repository(owner: "%s", name: "%s") {
    pullRequest(number: %s) {
      reviewThreads(first: 100) { nodes { isResolved } }
    }
  }
}''' % (owner, repo, number)
        conversations = {'resolved': False, 'unresolved': -1}
        gql = github_graphql(query, token)
        if '_err' not in gql:
            nodes = (gql.get('data', {})
                        .get('repository', {})
                        .get('pullRequest', {})
                        .get('reviewThreads', {})
                        .get('nodes', []))
            unresolved = sum(1 for n in nodes if not n.get('isResolved'))
            conversations = {'resolved': unresolved == 0, 'unresolved': unresolved}

        self._json({'ci': ci, 'conversations': conversations})

    def _post_comment(self, body):
        url = body.get('url', '')
        comment = body.get('body', '')
        if not url or not comment:
            return self._json({'error': 'Missing url or body'}, 400)
        try:
            owner, repo, number = parse_pr_url(url)
        except ValueError as e:
            return self._json({'error': str(e)}, 400)
        token = json.loads(CONFIG_FILE.read_text()).get('githubToken', '')
        if not token:
            return self._json({'error': 'No GitHub token configured — open Settings'}, 400)
        result = github(f'/repos/{owner}/{repo}/issues/{number}/comments', token, 'POST', {'body': comment})
        if '_err' in result:
            self._json({'error': result['_msg']}, 400)
        else:
            self._json({'ok': True, 'url': result.get('html_url', '')})

    def _file(self, filename, content_type):
        path = BASE_DIR / filename
        if not path.exists():
            return self._json({'error': f'{filename} not found'}, 404)
        content = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', f'{content_type}; charset=utf-8')
        self.send_header('Content-Length', len(content))
        self._cors()
        self.end_headers()
        self.wfile.write(content)

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', f'http://localhost:{PORT}')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        pass  # suppress request logs


if __name__ == '__main__':
    ensure_data()
    print(f'\033[1;33m⚡ Merginator 3000\033[0m is running at \033[1;36mhttp://localhost:{PORT}\033[0m')
    with http.server.HTTPServer(('127.0.0.1', PORT), Handler) as server:
        server.serve_forever()
