# Course Website Backend

This is the backend for a course website built with Flask. It includes user authentication, course management, assignment uploads, and lecture uploads.

## Setup

1. **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd backend
    ```

2. **Create a virtual environment and activate it:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Run the setup script:**
    ```bash
    ./setup.sh
    ```

## API Endpoints

### User Authentication

- **Register:** `POST /api/register`
- **Login:** `POST /api/login`

### Courses

- **Get Courses:** `GET /api/courses`
- **Get Course Details:** `GET /api/course/<course_id>`

### Teacher Endpoints

- **Upload Assignment:** `POST /api/teacher/upload-assignment`
- **View Submissions:** `GET /api/teacher/view-submissions`
- **Upload Lecture:** `POST /api/teacher/upload-lecture`

### Static Files

- **Serve Static Files:** `GET /static/<filename>`

## Running the Server

To run the Flask server, use the following command:
```bash
flask run
```

## License

This project is licensed under the MIT License.
