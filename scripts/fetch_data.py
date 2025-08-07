import os
import json
import logging
import argparse
import time
import re
import base64
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
MAX_REQUESTS = 100

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

    def list_repositories(self, since=0):
        """
        Lists all public repositories.
        """
        url = f"{self.BASE_URL}/repositories"
        params = {'since': since}
        response = self._make_request(url, params)
        return response.json() if response else []

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
        query = f"repo:{repo_full_name} is:issue is:open created:>{date_since}"
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
        url = f"{self.BASE_URL}/repos/{repo_full_name}/README.md"
        response = self._make_request(url)
        if not response:
            return ""
        try:
            content_b64 = response.json()['content']
            return base64.b64decode(content_b64).decode('utf-8')
        except (KeyError, UnicodeDecodeError) as e:
            logging.error(f"Could not fetch or decode README for {repo_full_name}: {e}")
            return ""

def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return {'last_repo_id': 0, 'projects': {}}
    with open(PROGRESS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            logging.warning(f"Could not decode {PROGRESS_FILE}. Starting from scratch.")
            return {'last_repo_id': 0, 'projects': {}}

def save_progress(last_repo_id, projects):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({'last_repo_id': last_repo_id, 'projects': projects}, f, indent=4)

def calculate_demand_index(new_stars, new_open_issues):
    """
    Calculates the demand index.
    """
    if new_stars > 0:
        return new_open_issues / new_stars
    return new_open_issues

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
    demand_index = calculate_demand_index(new_stars, new_open_issues)
    
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
        'demand_index': demand_index,
        'last_updated_repo': repo_details['updated_at'],
        'date_fetched': datetime.now(timezone.utc).isoformat()
    }

def save_projects_to_json(projects, filename):
    """
    Saves the project data to a JSON file.
    """
    project_list = list(projects.values())
    project_list.sort(key=lambda p: p['demand_index'], reverse=True)
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
    print (f"token: {len(token)}, {token[: 5]}, {token[-5: ]}")
    github_client = GitHubAPI(token)
    
    progress = load_progress()
    projects = progress['projects']
    last_repo_id = progress['last_repo_id']

    try:
        # Fetch new repositories
        logging.info(f"Fetching new repositories since ID {last_repo_id}")
        while github_client.request_count < MAX_REQUESTS:
            repos = github_client.list_repositories(since=last_repo_id)
            if not repos:
                break
            for repo in repos:
                project_data = process_repository(repo, github_client)
                if project_data:
                    projects[str(repo['id'])] = project_data
                last_repo_id = max(last_repo_id, repo['id'])
            if not repos:
                break

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        save_progress(last_repo_id, projects)
        save_projects_to_json(projects, args.output)

if __name__ == '__main__':
    main()
