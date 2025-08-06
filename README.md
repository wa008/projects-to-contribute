# Open Source Contribution-Minded Dashboard

This project is a dashboard that helps developers find open-source projects that are actively seeking contributions. It fetches data from GitHub, calculates a "demand index" for each project, and displays them in a sortable and filterable table.

## Features

- **Demand Index**: A metric calculated based on new stars and new open issues to identify projects that are popular but also need help.
- **Filter and Sort**: Filter projects by programming language or keyword, and sort them by various metrics like stars, new open issues, etc.
- **Daily Data Updates**: The project data is updated daily via a GitHub Actions workflow.

## How it Works

The dashboard is a simple static website that displays data from a `projects.json` file. This file is updated daily by a Python script (`scripts/fetch_data.py`) that runs as a GitHub Actions workflow.

The script fetches repositories from GitHub that have been created recently and have a certain number of stars. For each repository, it gathers more detailed information like the number of new stars, new open issues, and contributors. It then calculates the demand index and saves the data to `projects.json`.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/open-source-contribution-minded-dashboard.git
    ```
2.  **Install dependencies:**
    The project itself is a static website and has no dependencies. The data fetching script requires Python and the following libraries:
    ```bash
    pip install requests python-dotenv
    ```
3.  **Set up environment variables:**
    Create a `.env` file in the root directory and add your GitHub personal access token:
    ```
    GH_TOKEN=your_github_token
    ```
4.  **Run the data fetching script:**
    ```bash
    python scripts/fetch_data.py
    ```
5.  **Open `index.html` in your browser:**
    Open the `index.html` file in your web browser to see the dashboard.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.
