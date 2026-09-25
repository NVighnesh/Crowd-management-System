# 🚨 Crowd Management AI – Intelligent Crowd Monitoring & Management System

A full-stack AI-powered crowd management web application built using **React**, **FastAPI**, **Python**, **PostgreSQL**, and **Computer Vision**, designed for real-time crowd monitoring, people counting, camera management, zone-based monitoring, alert generation, and historical crowd analysis.

The application supports both **administrators** and **operators**, providing a complete workflow from user authentication and camera configuration to live monitoring, polygon-based zone management, crowd threshold detection, alerts, and historical analytics.

---

# 🔗 Project Links

* 💻 **GitHub Repository:** https://github.com/NVighnesh/Crowd-management-System
* 🌐 **Frontend:** Local React/Vite application
* ⚙️ **Backend API:** Local FastAPI application

---

# 📖 Introduction

The **Crowd Management AI** is a full-stack intelligent monitoring system developed to demonstrate the implementation of a real-world crowd monitoring and management platform.

The project follows a **React frontend + FastAPI REST API + PostgreSQL database + AI/Computer Vision** architecture.

Administrators can:

* Sign in securely
* Access the Admin Dashboard
* View system statistics
* Manage operator accounts
* Activate operators
* Deactivate operators
* Delete operators
* Manage cameras
* Configure monitoring zones
* Manage camera-related resources

Operators can:

* Sign in securely
* Access the Operator Dashboard
* Monitor cameras
* View live camera streams
* View total people counts
* View FPS and camera resolution
* View configured zones
* View recent alerts
* Configure camera zones
* Draw polygon monitoring zones
* Configure zone thresholds
* Configure counting points
* Use camera focus mode
* View zone trends
* View zone history
* View alert history

The application uses **PostgreSQL** as the persistent database and integrates AI/computer-vision processing for crowd monitoring.

---

# ✨ Features

## 🔐 Authentication Features

* User registration
* User login
* Authentication
* Role-based authorization
* Admin role
* Operator role
* Protected routes
* Protected APIs
* Persistent authentication state
* Active/inactive operator accounts
* Clear inactive account handling

---

## 👨‍💼 Admin Features

* Admin dashboard
* System statistics
* Operator management
* Operator activation
* Operator deactivation
* Operator deletion
* Camera management
* Camera configuration
* Zone management
* Camera monitoring
* Role-based dashboard access

---

## 👷 Operator Features

* Operator dashboard
* Live camera monitoring
* Camera cards
* Total people count
* FPS information
* Camera resolution
* Configured zones
* Recent zone alerts
* All-alerts panel
* Camera focus mode
* Zone trends
* Zone history
* Alert history
* Camera configuration
* Zone configuration

---

## 📹 Camera Features

* Add cameras
* View cameras
* Configure cameras
* Delete cameras
* Live camera streams
* Camera health information
* People counting
* FPS monitoring
* Resolution monitoring
* Camera-specific zones
* Camera-specific alerts
* Camera-specific historical data

---

## 📐 Zone Management Features

The application provides **polygon-based zone drawing** for camera monitoring.

Users can:

* Enter full-screen drawing mode
* Draw polygon zones directly on the camera
* Add multiple points
* View numbered points
* Clear current points
* Save zones
* Configure zone metadata
* Configure thresholds
* Configure counting points
* Reset drawing points
* Complete drawing mode
* View saved zones
* Reset saved zones
* Create multiple zones for one camera

### Zone Configuration

| Property       | Description                              |
| -------------- | ---------------------------------------- |
| Zone ID        | Unique identifier for the zone           |
| Zone Name      | Human-readable name of the zone          |
| Threshold      | Crowd threshold configured for the zone  |
| Counting Point | Counting configuration for the zone      |
| Polygon        | Coordinates defining the monitoring area |

---

## 🚨 Crowd Monitoring Features

The system processes camera/video data to monitor crowd conditions.

The monitoring functionality includes:

* People detection
* People counting
* Zone-based counting
* Crowd threshold comparison
* Crowd alerts
* Camera-specific alerts
* Zone-specific alerts
* Recent alerts
* Historical alerts
* Alert history

When a configured crowd threshold is reached, the system can generate an alert associated with the relevant camera and zone.

---

## 📊 Analytics Features

The application provides historical crowd monitoring information.

Analytics include:

* Total people count
* Zone-wise people counts
* Zone trend graphs
* Historical people counts
* Threshold reference lines
* Zone history
* Alert history
* Camera-specific historical information

---

## 🎯 Camera Focus Mode

Focus mode provides a detailed monitoring view for an individual camera.

It includes:

* Live camera feed
* Total people count
* FPS
* Resolution
* Zone information
* Zone trend graphs
* Zone history
* Alert history
* Camera-specific monitoring

---

## 🔔 Alert Features

The system provides camera and zone-specific alert information.

Alerts can be viewed through:

* Operator dashboard
* Camera cards
* All-alerts panel
* Camera focus mode
* Zone alert history
* Camera alert history

Alert records are stored in PostgreSQL and retrieved through backend APIs.

---

## 🔐 Security

The backend implements:

* Authentication
* Role-based authorization
* Protected REST APIs
* Admin/Operator access control
* Active/inactive account validation
* Environment-variable based configuration
* Database-backed user state
* Protected camera operations
* Protected zone operations

Sensitive configuration values are stored outside source code using environment variables.

---

# 🛠️ Functionalities

| Functionality     | Description                                |
| ----------------- | ------------------------------------------ |
| Authentication    | User registration and login                |
| Authorization     | Role-based Admin and Operator access       |
| User Management   | Activate, deactivate and delete operators  |
| Camera Management | Add, view, configure and delete cameras    |
| Live Monitoring   | Monitor live camera streams                |
| People Counting   | AI-based people counting                   |
| Zone Management   | Create and manage polygon monitoring zones |
| Thresholds        | Configure crowd thresholds                 |
| Counting Points   | Configure zone counting points             |
| Alerts            | Generate and display crowd alerts          |
| Focus Mode        | Detailed camera monitoring                 |
| Zone Trends       | Historical zone count visualization        |
| Zone History      | Historical zone monitoring records         |
| Alert History     | Camera and zone-specific alert history     |
| Database          | PostgreSQL persistence                     |
| REST APIs         | FastAPI backend services                   |
| Frontend          | React/Vite monitoring dashboard            |

---

# 💻 Tech Stack

## Frontend

* React
* JavaScript
* Vite
* React Router
* HTML
* CSS
* Dashboard UI components
* Chart/visualization components

## Backend

* Python
* FastAPI
* Uvicorn
* REST APIs
* Pydantic

## AI / Computer Vision

* Computer Vision
* People Detection
* People Counting
* Camera Processing
* Video Processing
* Zone-based Monitoring
* Crowd Threshold Analysis

## Database

* PostgreSQL
* SQL
* Relational Database
* Persistent Data Storage

## Development Tools

* Git
* GitHub
* VS Code
* Python Virtual Environment
* npm
* PowerShell

---

# 🏗️ Architecture

```text
                         ┌──────────────────────────┐
                         │          Users           │
                         │                          │
                         │   Admin    /   Operator  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │     React Frontend       │
                         │          Vite            │
                         │                          │
                         │ Dashboard / Monitoring   │
                         │ Camera / Zone UI         │
                         └────────────┬─────────────┘
                                      │
                                      │ REST API / HTTP
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │      FastAPI Backend     │
                         │                          │
                         │ Authentication           │
                         │ Camera APIs              │
                         │ Zone APIs                │
                         │ Alert APIs               │
                         │ Monitoring APIs          │
                         │ History APIs             │
                         └────────────┬─────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
          ┌────────────────┐  ┌────────────────┐  ┌───────────────┐
          │   PostgreSQL   │  │ AI / Computer  │  │ Camera / Video│
          │    Database    │  │ Vision Pipeline│  │    Sources    │
          │                │  │                │  │               │
          │ Users          │  │ Detection      │  │ Live Camera   │
          │ Cameras        │  │ Counting       │  │ Video Files   │
          │ Zones          │  │ Zone Analysis  │  │ Streams       │
          │ Alerts         │  │ Monitoring     │  │               │
          │ History        │  │                │  │               │
          └────────────────┘  └────────────────┘  └───────────────┘
```

---

# 🔄 Crowd Monitoring Flow

```text
Camera / Video Source
        │
        ▼
Video Frame Capture
        │
        ▼
AI / Computer Vision Processing
        │
        ▼
People Detection
        │
        ▼
People Counting
        │
        ▼
Zone Analysis
        │
        ▼
Compare Count With Threshold
        │
        ├───────────────────────┐
        │                       │
        ▼                       ▼
Within Threshold          Threshold Reached
        │                       │
        ▼                       ▼
Normal Monitoring          Generate Alert
                                │
                                ▼
                         Store Alert in DB
                                │
                                ▼
                         Display in Dashboard
```

---

# 🔄 Application Flow

```text
User
 │
 ▼
Login / Register
 │
 ▼
Authentication
 │
 ├───────────────────────┐
 │                       │
 ▼                       ▼
ADMIN                  OPERATOR
 │                       │
 ▼                       ▼
Admin Dashboard       Operator Dashboard
 │                       │
 ├── Operators           ├── Cameras
 │                       ├── Live Monitoring
 ├── Cameras             ├── Zones
 │                       ├── Alerts
 └── Zones               ├── Focus Mode
                         ├── Trends
                         └── History
```

---

# 📐 Zone Drawing Flow

```text
Select Camera
      │
      ▼
Enter Full-Screen Drawing Mode
      │
      ▼
Click Points on Camera
      │
      ▼
Create Polygon
      │
      ▼
Save Zone
      │
      ▼
Enter Zone Information
      │
      ├── Zone ID
      ├── Zone Name
      ├── Threshold
      └── Counting Point
      │
      ▼
Save
      │
      ▼
Persist Zone in PostgreSQL
      │
      ▼
Continue Drawing
      │
      ▼
Create Additional Zones
```

---

# 🚨 Alert Generation Flow

```text
Camera Frame
     │
     ▼
People Detection
     │
     ▼
People Count
     │
     ▼
Check Zone
     │
     ▼
Compare With Threshold
     │
     ├───────────────────────┐
     │                       │
     ▼                       ▼
Below Threshold         Threshold Reached
     │                       │
     ▼                       ▼
Normal State             Alert Generated
                             │
                             ▼
                       Save Alert
                             │
                             ▼
                    Display on Dashboard
```

---

# 🗄️ Database

The application uses **PostgreSQL** as its persistent relational database.

```text
PostgreSQL
    │
    ├── Users
    │
    ├── Cameras
    │
    ├── Zones
    │
    ├── Crowd Results
    │
    ├── Alerts
    │
    └── Historical Monitoring Data
```

The database stores persistent application information including:

* User accounts
* Operator active/inactive status
* Camera configuration
* Zone configuration
* Polygon coordinates
* Zone thresholds
* Counting point information
* Crowd results
* Alert records
* Historical monitoring data

The database acts as the source of truth for persistent application state.

---

# 📁 Project Structure

```text
CrowdManagementAI/
│
├── View_Outputs/
│   └── Project screenshots
│
├── trained-sample-videos/
│   └── Training/sample videos
│
├── demo-videos/
│   └── Demo/testing videos
│
├── src/
│   ├── api.py
│   ├── ...
│   └── Backend application modules
│
├── dashboard/
│   ├── public/
│   ├── src/
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.*
│
├── configs/
│   └── Configuration files
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# 🖼️ Application Screenshots

The `View_Outputs` folder contains screenshots of the application's actual outputs and UI.

## 🔐 Authentication

* Login
* Registration
* Role-based navigation

## 👨‍💼 Admin Dashboard

* Admin dashboard
* System statistics
* Operator management
* Operator activation
* Operator deactivation
* Operator deletion
* Camera management

## 👷 Operator Dashboard

* Operator dashboard
* Camera monitoring
* Live camera cards
* People count
* FPS
* Resolution
* Recent alerts
* All-alerts panel

## 📹 Camera Management

* Camera configuration
* Camera information
* Camera deletion
* Camera monitoring

## 📐 Zone Management

* Full-screen zone drawing
* Polygon creation
* Zone configuration
* Zone threshold configuration
* Counting point configuration
* Multiple zone creation
* Zone reset

## 🎯 Focus Mode

* Live camera
* People count
* Zone information
* Zone trend graphs
* Zone history
* Alert history
* Camera-specific monitoring

All screenshots are available directly inside the repository:

```text
View_Outputs/
```

---

# 🎥 Sample & Demo Videos

The repository contains intentionally included video assets for project demonstration and testing.

## 🧠 Training / Sample Videos

```text
trained-sample-videos/
```

This folder contains training/sample videos used during project development and demonstration.

## 🎬 Demo Videos

```text
demo-videos/
```

This folder contains demo/testing videos that can be used to demonstrate the crowd monitoring functionality.

These folders are intentionally included in GitHub.

---

# 🧪 Testing & Build

## Backend

The backend provides APIs for:

* Authentication
* Users
* Cameras
* Zones
* Alerts
* Monitoring
* Historical data

The health endpoint can be used to check backend and database status:

```text
/health
```
---

# 🔄 Backend Processing Flow

```text
React Frontend
      │
      ▼
FastAPI REST API
      │
      ├──────────────────┐
      │                  │
      ▼                  ▼
PostgreSQL          AI / CV Pipeline
      │                  │
      │                  ├── Frame Processing
      │                  ├── Detection
      │                  ├── Counting
      │                  └── Zone Analysis
      │
      ▼
Historical Data
      │
      ▼
Alerts / Analytics
      │
      ▼
React Dashboard
```

---

# ⚡ Performance Considerations

The application uses database and frontend optimizations for monitoring and historical data retrieval.

These include:

* Camera-specific database queries
* Zone-specific filtering
* Limited recent-alert retrieval
* Historical data filtering
* Avoiding unnecessary repeated historical requests
* Targeted API retrieval
* Persistent PostgreSQL storage
* Efficient retrieval of recent monitoring information

Historical information is retrieved from PostgreSQL instead of repeatedly processing the complete historical dataset on the frontend.

---

# 🎯 Project Goals

This project was developed to demonstrate practical full-stack, AI, and software engineering concepts including:

* Python backend development
* FastAPI
* REST API development
* React development
* Vite
* PostgreSQL
* Database persistence
* Authentication
* Role-based authorization
* Camera management
* Computer vision
* People counting
* Crowd monitoring
* Polygon-based zone management
* Threshold-based alerting
* Real-time monitoring
* Historical analytics
* Data visualization
* API integration
* Database query optimization
* Git/GitHub
* Full-stack application architecture

---

# 📚 Learning Outcomes

Through this project, the following concepts were implemented and practiced:

* Full-stack application development
* FastAPI backend development
* React frontend development
* REST API architecture
* PostgreSQL integration
* Authentication and authorization
* Role-based access control
* Computer vision integration
* Video processing
* People counting
* Real-time monitoring
* Polygon coordinate handling
* Threshold-based event detection
* Alert persistence
* Historical data retrieval
* Data visualization
* Frontend/backend integration
* Database optimization
* Git/GitHub workflow

---

## 📸 Screenshots

**Final Outputs**
[Click Here](View_Outputs/)

---

## 👤 Author

**NEDULLA VIGHNESH**  
- GitHub: [2200032267](https://github.com/NVighnesh)  
- LinkedIn: [N VIGHNESH](https://www.linkedin.com/in/n-vighnesh-5b74aa24a)  
- Email:vighneshnv2@gmail.com
---
## ⭐ Star This Repository

If you find this project useful or interesting, please ⭐ star this repository to support and encourage further development!  
Your support means a lot! 🙏

---

# 📜 License

This project is developed for learning, portfolio, research, and demonstration purposes.
