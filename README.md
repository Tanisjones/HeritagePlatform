# Heritage Platform

A comprehensive platform for crowdsourcing, managing, and showcasing cultural heritage data.

## Overview

The Heritage Platform is designed to help communities and organizations preserve their cultural heritage. It supports:
- **Composite Data Objects (CDO)**: Handling tangible and intangible heritage with rich multimedia support (images, audio, video, documents).
- **Geospatial Management**: Precise location tracking and map-based exploration using Leaflet and PostGIS.
- **Crowdsourcing**: Public contributions with a guided wizard and moderation workflow.
- **Gamification**: Rewarding user engagement (contributions, annotations) with points and levels.
- **Educational Resources**: Integration with LOM (Learning Object Metadata) standards.
- **Offline Support**: Ability to download search results for offline exploration.

## Technology Stack

### Backend
- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL 15 + PostGIS (Geospatial data)
- **AI Integration**: Custom service layer for content generation/enhancement
- **Containerization**: Docker & Docker Compose

### Frontend
- **Framework**: Vue 3 (Composition API)
- **Key Libraries**:
    - **Pinia**: State management
    - **Vue Router**: Navigation
    - **TailwindCSS**: Styling
    - **Leaflet (@vue-leaflet)**: Maps
    - **Vue I18n**: Internationalization (EN/ES)

## Project Structure

```
.
├── backend/                # Django project
│   ├── apps/               # Modular Django apps
│   │   ├── heritage/       # Core heritage models and views
│   │   ├── users/          # Custom user model & roles
│   │   ├── gamification/   # Points and leaderboards
│   │   ├── education/      # LOM metadata
│   │   └── ...
│   └── ...
├── frontend/               # Vue 3 application
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── views/          # Page views
│   │   ├── stores/         # Pinia stores
│   │   └── services/       # API clients
│   └── ...
├── docker/                 # Docker configuration files
└── docker-compose.yml      # Service orchestration
```

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Quick Start (Docker)

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd HeritagePlatform
    ```

2.  **Start the services**:
    ```bash
    docker-compose up --build
    ```

3.  **Access the application**:
    - Frontend: `http://localhost:8080`
    - Backend API: `http://localhost:8080/api/v1`
    - Admin Panel: `http://localhost:8080/admin`

### Local Development

#### Backend
1.  Navigate to `backend/`:
    ```bash
    cd backend
    ```
2.  Create a virtual environment and activate it:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run migrations and start server:
    ```bash
    python manage.py migrate
    python manage.py runserver
    ```

#### Frontend
1.  Navigate to `frontend/`:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start development server:
    ```bash
    npm run dev
    ```

## Contributing
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes.
4.  Push to the branch.
5.  Open a Pull Request.

## License
GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
