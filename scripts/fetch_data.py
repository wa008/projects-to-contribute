import os
import json
import logging
import argparse
import time
import re
import base64
import shutil
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Constants
TOPIC_MAP = {
    'web': ['web', 'website', 'webapp', 'frontend', 'backend', 'fullstack', 'http', 'server', 'nextjs', 'react', 'vue'],
    'ai': ['ai', 'ml', 'artificial-intelligence', 'machine-learning', 'deep-learning', 'nlp', 'computer-vision', 'llm', 'agent'],
    'database': ['database', 'sql', 'nosql', 'storage'],
    'mobile': ['mobile', 'android', 'ios', 'flutter', 'react-native'],
    'game': ['game', 'gamedev', 'gaming', 'unity', 'unreal'],
    'cli': ['cli', 'command-line', 'terminal', 'shell'],
    'data-science': ['data-science', 'data-analysis', 'data-visualization', 'pandas', 'numpy', 'jupyter'],
    'devops': ['devops', 'docker', 'kubernetes', 'ci-cd', 'automation', 'terraform'],
    'security': ['security', 'cybersecurity', 'vulnerability', 'pentesting'],
    'blockchain': ['blockchain', 'crypto', 'web3'],
    'framework': ['framework', 'library'],
    'testing': ['testing', 'test', 'tdd', 'bdd'],
    'tool': ['tool', 'utility', 'plugin'],
}

ACRONYMS = ['AI', 'ML', 'NLP', 'API', 'CLI', 'CI-CD', 'SQL']
PROGRESS_FILE = 'progress.json'
MAX_REQUESTS = 2000

class GitHubAPI:
    """
    A client for interacting with the GitHub API.
    """
    BASE_URL = 'https://api.github.com'

    def __init__(self, token):
        if not token:
            raise ValueError("GitHub token not found.")
        self._headers = {'Authorization': f'token {token}'}
        self.request_count = 0

    def _make_request(self, url, params=None):
        if self.request_count >= MAX_REQUESTS:
            raise Exception("Request limit reached")
        self.request_count += 1
        time.sleep(1)
        try:
            response = requests.get(url, headers=self._headers, params=params)
            logging.info(f"Request to {url} with params {params} returned status {response.status_code}")
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            return None

    def list_repositories(self, created_date_str, pushed_date_str, page=1, per_page=100):
        """
        Lists all public repositories created on a specific date and pushed recently.
        """
        min_stars = 50
        query = f'stars:>{min_stars} created:{created_date_str} pushed:>{pushed_date_str}'
        url = f"{self.BASE_URL}/search/repositories"
        params = {'q': query, 'page': page, 'per_page': per_page, 'sort': 'created', 'order': 'asc'}
        response = self._make_request(url, params)
        if response:
            return response.json().get('items', [])
        return []

    def search_repositories(self, query, sort='stars', order='desc', per_page=100, page=1):
        """
        Searches for repositories using the given query.
        """
        url = f"{self.BASE_URL}/search/repositories"
        params = {'q': query, 'sort': sort, 'order': order, 'per_page': per_page, 'page': page}
        response = self._make_request(url, params)
        return response.json().get('items', []) if response else []

    def get_repo_details(self, repo_full_name):
        """
        Gets detailed information for a single repository.
        """
        url = f"{self.BASE_URL}/repos/{repo_full_name}"
        response = self._make_request(url)
        return response.json() if response else None

    def get_recent_open_issues_count(self, repo_full_name, days_ago=30):
        """
        Gets the count of open issues created in the last N days for a repository.
        """
        date_since = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        query = f"repo:{repo_full_name} is:issue is:open created:>{date_since} -author:app/bot"
        url = f"{self.BASE_URL}/search/issues"
        params = {'q': query, 'per_page': 1}
        response = self._make_request(url, params)
        return response.json().get('total_count', 0) if response else 0

    def get_new_stars_count(self, repo_full_name, days_ago=30):
        """
        Counts the number of stars (WatchEvents) in the last N days.
        """
        url = f"{self.BASE_URL}/repos/{repo_full_name}/events"
        params = {'per_page': 100}
        count = 0
        date_since = datetime.now(timezone.utc) - timedelta(days=days_ago)
        page = 1
        while True:
            params['page'] = page
            response = self._make_request(url, params)
            if not response:
                break
            events = response.json()
            if not events:
                break
            for event in events:
                event_created_at = datetime.fromisoformat(event['created_at'].replace('Z', '+00:00'))
                if event_created_at < date_since:
                    return count
                if event['type'] == 'WatchEvent':
                    count += 1
            if "next" not in response.links:
                break
            page += 1
            if page > 3: # GitHub Events API is limited to 300 events (3 pages)
                break
        return count

    def get_contributors_count(self, repo_full_name):
        """
        Gets the total number of contributors for a repository.
        """
        url = f"{self.BASE_URL}/repos/{repo_full_name}/contributors"
        params = {'per_page': 1, 'anon': 'true'}
        response = self._make_request(url, params)
        if not response or response.status_code == 204:
            return 0
        if 'Link' in response.headers:
            link_header = response.headers['Link']
            match = re.search(r'&page=(\d+)>; rel="last"', link_header)
            if match:
                return int(match.group(1))
        return len(response.json())

    def get_readme(self, repo_full_name):
        """
        Fetches and decodes the README content for a repository.
        """
        for readme_name in ('README.md', 'readme', 'README', 'readme.md'):
            url = f"{self.BASE_URL}/repos/{repo_full_name}/{readme_name}"
            response = self._make_request(url)
            if not response:
                logging.info(f"{readme_name} doesn't exist")
                continue
            try:
                content_b64 = response.json()['content']
                return base64.b64decode(content_b64).decode('utf-8')
            except (KeyError, UnicodeDecodeError) as e:
                logging.info(f"Could not fetch or decode {readme_name} for {repo_full_name}: {e}")
        return ""

    def _count_code_lines(repo_path="."):
        """
        Calculates the total number of lines in code files within a specified path.

        :param repo_path: str, The path to the repository or directory to scan.
        """
        include_extensions = {
            # Web Development (Frontend)
            '.html', '.htm', '.xhtml', '.vue', '.svelte',
            '.css', '.scss', '.sass', '.less',
            '.js', '.mjs', '.cjs', '.ts', '.jsx', '.tsx',

            # Web Development (Backend)
            '.go', '.php', '.rb', '.erb', '.java', '.jsp',
            '.py', '.rs', '.ex', '.exs', '.pl', '.pm',

            # Application & Systems Programming
            '.c', '.h', '.cpp', '.hpp', '.cxx', '.hxx',
            '.cs', '.swift', '.m', '.mm', '.kt', '.kts', '.scala',
            '.dart', '.lua', '.groovy', '.clj', '.cljs', '.cljc',
            '.hs', '.erl', '.hrl', '.vb', '.zig',
            
            # Scripting
            '.sh', '.bash', '.ps1', '.bat', '.cmd', 'Makefile',

            # Data & Configuration
            '.xml', '.json', '.yaml', '.yml', '.toml', '.ini',
            '.sql', '.graphql', '.gql', '.properties', 'Dockerfile',
        }
        exclude_dirs = {
            '.git', '.idea', '.vscode', '__pycache__', 'node_modules', 
            'vendor', 'build', 'dist', 'target', 'venv'
        }
        total_line_count = 0
        for root, dirs, files in os.walk(repo_path, topdown=True):
            # Remove excluded directories from the list of directories to traverse.
            # Modifying dirs[:] in-place is necessary for os.walk to respect the changes.
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # Check if the file extension is in the include list
                if any(file.endswith(ext) for ext in include_extensions):
                    file_path = os.path.join(root, file)
                    print (file_path)
                    try:
                        # Open file with 'utf-8' encoding, ignoring errors for binary files
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            total_line_count += sum(1 for line in f)
                    except Exception as e:
                        print(f"Could not read file {file_path}: {e}")
                        
        return total_line_count
        
    def get_code_line_count(self, repo_full_name, repo_size):
        """
        Gets the line count of code in a repository.
        """
        try:
            _, _, free = shutil.disk_usage(".")
            print (f"free: {free}, repo_size: {repo_size}")
            if repo_size * 1024 > free and repo_size / 1024 > 500: # > 500MB
                logging.warning(f"Skipping {repo_full_name} due to insufficient disk space or > 500MB.")
                return 0
        except Exception as e:
            logging.warning(f"Could not check disk space: {e}")

        repo_url = f'https://github.com/{repo_full_name}.git'
        repo_name = repo_full_name.split('/')[1]
        os.system(f'git clone {repo_url} --depth 1')
        line_count = self._count_code_lines(repo_name)
        print (f"repo_full_name: {repo_full_name}, repo_name: {repo_name}, line_count: {line_count}")
        os.system(f'rm -rf {repo_name}')
        return int(line_count.split()[-2])

def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        start_date = '2008-01-01'
        return {'last_processed_created_date': start_date, 'projects': {}}
    with open(PROGRESS_FILE, 'r') as f:
        try:
            data = json.load(f)
            if 'last_processed_created_date' not in data:
                start_date = '2008-01-01'
                data['last_processed_created_date'] = start_date
        except json.JSONDecodeError:
            logging.warning(f"Could not decode {PROGRESS_FILE}. Starting from scratch.")
            start_date = '2008-01-01'
            data = {'last_processed_created_date': start_date}

    projects = {}
    if os.path.exists('projects.json'):
        with open('projects.json', 'r') as f:
            try:
                projects_data = json.load(f)
                if 'projects' in projects_data:
                    projects = {str(p['id']): p for p in projects_data['projects']}
            except json.JSONDecodeError:
                logging.warning("Could not decode projects.json. Starting with an empty project list.")

    return {'last_processed_created_date': data['last_processed_created_date'], 'projects': projects}

def save_progress(last_processed_created_date):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({'last_processed_created_date': last_processed_created_date}, f, indent=4)

def generate_keywords(topics, description, readme_content, language):
    """
    Generates 2-3 keywords from topics, description, and language.
    """
    normalized = set()
    # First pass: from topics
    for topic in topics:
        for general_topic, specific_topics in TOPIC_MAP.items():
            if topic.lower() in specific_topics:
                normalized.add(general_topic)

    # Second pass: from description and README if we need more keywords
    text_to_search = (description.lower() if description else '') + ' ' + readme_content.lower()
    if len(normalized) < 3:
        for word in re.split(r'\s+|,|\.', text_to_search):
            for general_topic, specific_topics in TOPIC_MAP.items():
                if word in specific_topics and general_topic not in normalized:
                    normalized.add(general_topic)
                    if len(normalized) >= 3:
                        break
            if len(normalized) >= 3:
                break
    
    final_keywords = []
    for k in list(normalized)[:3]:
        if k.upper() in ACRONYMS:
            final_keywords.append(k.upper())
        else:
            final_keywords.append(k.capitalize())

    if not final_keywords and language and language != 'N/A':
        return [language]

    return final_keywords if final_keywords else ['Tool']

def process_repository(repo, github_client, days_ago=30):
    """
    Processes a single repository to gather all necessary data.
    """
    logging.info(f"Processing {repo['full_name']}...")
    
    repo_details = github_client.get_repo_details(repo['full_name'])
    if not repo_details:
        return None

    contributors = github_client.get_contributors_count(repo['full_name'])
    new_open_issues = github_client.get_recent_open_issues_count(repo['full_name'], days_ago)
    new_stars = github_client.get_new_stars_count(repo['full_name'], days_ago)
    readme_content = github_client.get_readme(repo['full_name'])
    keywords = generate_keywords(repo_details.get('topics', []), repo_details.get('description', ''), readme_content, repo_details.get('language'))
    code_line_count = github_client.get_code_line_count(repo['full_name'], repo_details['size'])

    return {
        'id': repo_details['id'],
        'name': repo_details['full_name'],
        'url': repo_details['html_url'],
        'stars': repo_details['stargazers_count'],
        'language': repo_details.get('language', 'N/A'),
        'keywords': keywords,
        'new_open_issues': new_open_issues,
        'new_stars_30d': new_stars,
        'contributors': contributors,
        'code_line_count': code_line_count,
        'last_updated_repo': repo_details['updated_at'],
        'pushed_at': repo_details['pushed_at'],
        'date_fetched': datetime.now(timezone.utc).isoformat()
    }

def save_projects_to_json(projects, filename):
    """
    Saves the project data to a JSON file.
    """
    project_list = list(projects.values())
    output = {
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'projects': project_list
    }
    try:
        with open(filename, 'w') as f:
            json.dump(output, f, indent=4)
        logging.info(f"Data saved to {filename}")
    except IOError as e:
        logging.error(f"Failed to write to {filename}: {e}")

def main():
    """
    Main function to orchestrate the data fetching and processing.
    """
    parser = argparse.ArgumentParser(description="Fetch GitHub repository data.")
    parser.add_argument(
        '--output',
        default='projects.json',
        help='The output file for the project data.'
    )
    parser.add_argument(
        '--token',
        help='GH TOKEN'
    )
    args = parser.parse_args()
    if args.token is not None:
        token = args.token
    else:
        token = os.environ.get('GH_TOKEN')
    github_client = GitHubAPI(token)
    
    progress = load_progress()
    projects = progress.get('projects', {})
    last_processed_created_date_str = progress.get('last_processed_created_date')

    last_successful_created_date_str = last_processed_created_date_str
    try:
        start_date = datetime.strptime(last_processed_created_date_str, '%Y-%m-%d').date()
        end_date = datetime.now(timezone.utc).date()
        pushed_date_str = (datetime.now(timezone.utc) - timedelta(days=180)).strftime('%Y-%m-%d')

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            logging.info(f"Processing repositories created on {date_str}...")
            
            page = 1
            per_page = 100
            while True: # Pagination loop
                if github_client.request_count >= MAX_REQUESTS:
                    raise Exception("Request limit reached for this run.")

                repos = github_client.list_repositories(date_str, pushed_date_str, page=page, per_page=per_page)
                if not repos:
                    logging.info(f"No more repositories found for {date_str}.")
                    break
                
                for repo in repos:
                    if str(repo['id']) not in projects:
                        project_data = process_repository(repo, github_client)
                        if project_data:
                            projects[str(repo['id'])] = project_data
                
                if len(repos) < per_page:
                    break
                
                page += 1
            
            last_successful_created_date_str = date_str
            current_date += timedelta(days=1)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        save_progress(last_successful_created_date_str)
        logging.info(f"Successfully processed and saved progress for {last_successful_created_date_str}.")
        save_projects_to_json(projects, args.output)

if __name__ == '__main__':
    main()
