# AI Multi-Agent Calendar Scheduler

## Overview
The **AI Multi-Agent Calendar Scheduler** is an advanced scheduling system that leverages natural language processing, multi-agent orchestration, and modern APIs to handle meeting scheduling, rescheduling, and conflict resolution. Built to be user-friendly and extensible, the system offers core features like conflict resolution, learning from feedback, and integration with email for scheduling requests.

---

## Features

### Core Functionalities
- **Natural Language Understanding:**
  - Parses email inputs or direct API requests to extract intent, dates, times, attendees, and actions (e.g., schedule, reschedule, cancel).

- **Email Integration:**
  - Monitors Gmail for scheduling-related emails and processes them dynamically.

- **Google Calendar Integration:**
  - Directly interacts with the Google Calendar API to create, modify, or delete events.

- **Scheduling and Rescheduling:**
  - Handles new meeting scheduling and reschedules conflicts by proposing alternate time slots.

- **Conflict Resolution:**
  - Detects time conflicts in Google Calendar and resolves them intelligently.

- **Feedback and Learning:**
  - Captures user feedback and adapts decision-making over time using logged data.

---

## Technologies Used

### Backend
- **FastAPI:** Backend framework for managing APIs and agent interactions.
- **SQLite:** Database for storing user, meeting, and feedback data.
- **Ray:** Multi-agent orchestration for concurrent scheduling, rescheduling, and conflict resolution.
- **Google Calendar API:** Real-time integration for managing events.

### Natural Language Processing
- **OpenAI GPT-4 API:**
  - Processes natural language inputs.
  - Extracts intents and entities using fine-tuned prompts for Named Entity Recognition (NER).

### Frontend
- **React with Material-UI:**
  - Displays meeting lists, details, conflicts, and feedback in a clean, professional UI.
  - Responsive and user-friendly interface.

### Integration
- **Google Gmail API:**
  - Monitors inbox for scheduling-related emails.
  - Processes emails for scheduling requests dynamically.

---

## Current Features

### Backend
- **Agents:**
  - `schedule_meeting`: Schedules meetings based on user input.
  - `reschedule_meeting`: Proposes alternate times for rescheduling.
  - `resolve_conflict`: Resolves conflicts by suggesting new slots.
  - `learn_from_feedback`: Captures and processes feedback to improve decision-making.

- **API Endpoints:**
  - `/schedule`: Handles scheduling requests.
  - `/reschedule`: Manages rescheduling with conflict resolution.
  - `/cancel`: Cancels existing meetings.
  - `/feedback`: Captures user feedback for learning.
  - `/meetings`: Fetches all stored meetings and their details.

- **Database Tables:**
  - `users`: Stores user details and preferences.
  - `meetings`: Stores meeting information (title, date, time, attendees, status).
  - `feedback`: Logs user feedback (rating, comments) for learning.

### Frontend
- **Professional UI:**
  - Displays a meeting list in a tabular format with filters for status.
  - Provides detailed views of selected meetings, including attendees and feedback.
  - Shows conflicts and resolutions dynamically.

---

## Future Enhancements

### Real-Time Learning System
- Implement reinforcement learning to adapt and improve based on user feedback.
- Allow the system to autonomously suggest optimized meeting schedules by analyzing past interactions.

### Custom LLM Development
- Fine-tune a lightweight LLM model on scheduling-related data for faster and offline processing.
- Extend support for multilingual inputs and regional preferences.

### Advanced Conflict Resolution
- Allow users to set meeting priorities and preferences (e.g., prefer mornings).
- Introduce automated notifications for conflicts and resolutions.

### Enhanced Analytics
- Add a dashboard with analytics showing meeting trends, feedback scores, and learning improvements.

---

## Learning System and Reinforcement

### Feedback Mechanism
- Users rate scheduling suggestions (1-5 stars) and provide comments.
- Feedback is logged and processed to improve agent suggestions.

### Adaptive Agents
- The `learn_from_feedback` agent adjusts decision-making rules dynamically.
- Use reinforcement learning to optimize conflict resolution and scheduling efficiency.

---

## Setup and Installation

### Prerequisites
- Python 3.9+
- Node.js and npm for the frontend
- Access to OpenAI GPT API and Google Gmail API

### Steps to Run

1. **Backend:**
   - Install Python dependencies:
     ```bash
     pip install -r requirements.txt
     ```
   - Initialize the database:
     ```bash
     python init_db.py
     ```
   - Gmail and Calender API Integration
      - Place credentials.json in the project root directory. This file is obtained from your Google Cloud project.
      - Run authorize.py to generate token.json for authenticated access:
     ```bash
     python authorize.py
     ```
   - Start the backend server:
     ```bash
     uvicorn main:app --reload
     ```

2. **Frontend:**
   - Navigae to frontend Directory:
     ```bash
     cd scheduler-frontend
     ``` 
   - Install dependencies:
     ```bash
     npm install
     ```
   - Start the development server:
     ```bash
     npm start
     ```

3. **Environment Variables:**
   - Set the `OPENAI_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS` for integration with GPT-4 and Gmail API.

---

## Example Scenarios

### Scheduling a Meeting
- **Input:** *"Schedule a meeting with Alex next Tuesday at 3 PM."*
- **Output:** *"Meeting scheduled with Alex on Tuesday, 2024-12-05, at 3 PM."*

### Rescheduling a Meeting
- **Input:** *"Reschedule my meeting with Alex to 4 PM."*
- **Output:** *"Meeting rescheduled with Alex to 2024-12-05 at 4 PM."*

### Conflict Resolution
- **Input:** *"Schedule a meeting with Alex and Bob at 3 PM tomorrow."*
- **Conflict:** *"Alex is unavailable at 3 PM."*
- **Output:** *"Alex is unavailable at 3 PM. How about 4 PM?"*


### Google Calendar Integration
- Meetings are directly added to Google Calendar when scheduled.

Features:
 - Creates events with title, time, and attendees.
 - Reschedules events if requested.
 - Deletes events when canceled.

---