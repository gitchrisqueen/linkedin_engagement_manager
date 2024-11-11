# LinkedIn Engagement Manager (LEM)

## Overview

LinkedIn Engagement Manager (LEM) is an automated solution for managing engagement and post interactions on LinkedIn. This tool allows users to automate the process of commenting, sending direct messages (DMs), responding to comments, and scheduling posts. All content (text, carousels, videos) is AI-generated and passes through sentiment analysis for appropriateness. LEM also includes a preview and approval system, enabling manual or automated approval of content.

## Key Features
- **Automated Engagement**: Commenting, messaging profile viewers, and replying to post comments with scheduled engagement tasks.
- **AI-Generated Content**: Modular AI services generate carousel, text, and video content.
- **Sentiment Analysis**: Ensures content is appropriate, aligned with user preferences.
- **Approval Workflow**: Preview and approve content before publishing or allow for automatic approval.
- **Video Creation**: Generate videos from prompts using AI.
- **Summarizing Recent Activity**: Summarize recent LinkedIn activities and craft personalized responses.
- **Date-Time Picker for Scheduled Posts**: Edit scheduled posts with a date-time picker for easy scheduling.
- **Dockerized Environment**: Easily deployable to the cloud using Docker containers.
- **Modular Design**: Content generation modules can be swapped out for any SaaS services.
- **User Dashboard**: Mobile and web-friendly dashboard for monitoring and controlling the engagement process.

## Tech Stack
- **Python** with **Selenium** for automation tasks.
- **MySQL** as the relational database.
- **Docker** to containerize the application for local development and cloud deployment.
- **AI Services**: Integrated AI models to generate content and perform sentiment analysis.
- **Streamlit** for the user interface.

## Getting Started

### Prerequisites
1. **Docker** installed on your system.
2. **Python 3.9+** for local development.
3. **MySQL 8.0** or above (can be run inside Docker).
4. **Streamlit** for running the user interface.
5. Necessary API keys for AI services (e.g., OpenAI API key).

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/linkedin-engagement-manager.git
   cd linkedin-engagement-manager
   ```

2. Set up the environment:
   ```bash
   cp .env.example .env
   # Fill in necessary API keys, MySQL credentials, etc.
   ```

3. Build and run the Docker containers:
   ```bash
   docker-compose up --build
   ```

4. Access the web dashboard:
   Open [http://localhost:5000](http://localhost:5000) in your browser.

### Running the Automation Scripts
1. Make sure Docker containers are running.
2. Use the following command to trigger Selenium automation:
   ```bash
   docker exec -it selenium-app python run_automation.py
   ```

### Contributing
We welcome contributions to the project. Please submit a pull request with clear documentation of any changes.

## License
MIT License.
