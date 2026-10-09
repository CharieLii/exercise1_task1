# NoteTaker - Personal Note Management Application

A modern, responsive web application for managing personal notes with a beautiful user interface and full CRUD functionality.

## 🌟 Features

- **Create Notes**: Add new notes with titles and rich content
- **Edit Notes**: Update existing notes with real-time editing
- **Delete Notes**: Remove notes you no longer need
- **Search Notes**: Find notes quickly by searching titles and content
- **Auto-save**: Notes are automatically saved as you type
- **Responsive Design**: Works perfectly on desktop and mobile devices
- **Modern UI**: Beautiful gradient design with smooth animations
- **Real-time Updates**: Instant feedback and updates

## 🚀 Live Demo

The application is deployed and accessible at: **https://3dhkilc88dkk.manus.space**

## 🛠 Technology Stack

### Frontend
- **HTML5**: Semantic markup structure
- **CSS3**: Modern styling with gradients, animations, and responsive design
- **JavaScript (ES6+)**: Interactive functionality and API communication

### Backend
- **Python Flask**: Web framework for API endpoints
- **SQLAlchemy**: ORM for database operations
- **Flask-CORS**: Cross-origin resource sharing support

### Database
- **SQLite**: Lightweight, file-based database for data persistence

## 📁 Project Structure

```
notetaking-app/
├── src/
│   ├── models/
│   │   ├── user.py          # User model (template)
│   │   └── note.py          # Note model with database schema
│   ├── routes/
│   │   ├── user.py          # User API routes (template)
│   │   └── note.py          # Note API endpoints
│   ├── static/
│   │   ├── index.html       # Frontend application
│   │   └── favicon.ico      # Application icon
│   ├── database/
│   │   └── app.db           # SQLite database file
│   └── main.py              # Flask application entry point
├── venv/                    # Python virtual environment
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🔧 Local Development Setup

### Prerequisites
- Python 3.11+
- pip (Python package manager)

### Installation Steps

1. **Clone or download the project**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment**
   ```bash
   source venv/bin/activate
   ```

   Remark: On Windows, use `venv\Scripts\activate`

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python src/main.py
   ```

5. **Access the application**
   - Open your browser and go to `http://localhost:5001`

## Command-line Translation

After installing the dependencies, set `open_router_key` in the root `.env`
file. This file is ignored by Git. The translator uses OpenRouter's
`deepseek/deepseek-v4-flash` model and defaults to Simplified Chinese:

```bash
python translator.py "How are you?"
python translator.py "你好" --target-language English
```

The program prints only the translated text on success. API calls use your
OpenRouter account credits. This standalone script can also be imported via
`from translator import llm_generate`.

## 📡 API Endpoints

### Note Translation

Select a note or create a draft, choose a target language, and click **Translate**.
The translated title and content appear in the editor. Click **Save** to persist
them. Translation errors leave the original draft intact. Both saved notes and
unsaved drafts are supported. Translation does not automatically save a note.

The system prompt lives in `prompts/translate_prompt.md`. The backend requests
structured JSON from OpenRouter and validates it before updating the editor.
The API key is read on the server from `.env` (`open_router_key`).

`POST /api/notes/translate` accepts:

```json
{"title": "Greeting", "content": "How are you?", "target_language": "Simplified Chinese"}
```

The JSON response has this shape:

```json
{"title": "问候", "content": "你好吗？", "target_language": "Simplified Chinese"}
```

Supported languages: Simplified Chinese, Traditional Chinese, English, Japanese,
Korean, French, Spanish, and German. Titles are limited to 200 characters and
content to 20,000 characters per translation request. Invalid requests return
HTTP 400; model/configuration failures return HTTP 502, both with a JSON `error`.

### Notes API
- `GET /api/notes` - Get all notes
- `POST /api/notes` - Create a new note
- `GET /api/notes/<id>` - Get a specific note
- `PUT /api/notes/<id>` - Update a note
- `DELETE /api/notes/<id>` - Delete a note
- `GET /api/notes/search?q=<query>` - Search notes

### Request/Response Format
```json
{
  "id": 1,
  "title": "My Note Title",
  "content": "Note content here...",
  "created_at": "2025-09-03T11:26:38.123456",
  "updated_at": "2025-09-03T11:27:30.654321"
}
```

## 🎨 User Interface Features

### Sidebar
- **Search Box**: Real-time search through note titles and content
- **New Note Button**: Create new notes instantly
- **Notes List**: Scrollable list of all notes with previews
- **Note Previews**: Show title, content preview, and last modified date

### Editor Panel
- **Title Input**: Edit note titles
- **Content Textarea**: Rich text editing area
- **Save Button**: Manual save option (auto-save also available)
- **Delete Button**: Remove notes with confirmation
- **Real-time Updates**: Changes reflected immediately

### Design Elements
- **Gradient Background**: Beautiful purple gradient backdrop
- **Glass Morphism**: Semi-transparent panels with backdrop blur
- **Smooth Animations**: Hover effects and transitions
- **Responsive Layout**: Adapts to different screen sizes
- **Modern Typography**: Clean, readable font stack

## 🔒 Database Schema

### Notes Table
```sql
CREATE TABLE note (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🚀 Deployment

The application is configured for easy deployment with:
- CORS enabled for cross-origin requests
- Host binding to `0.0.0.0` for external access
- Production-ready Flask configuration
- Persistent SQLite database

## 🔧 Configuration

### Environment Variables
- `FLASK_ENV`: Set to `development` for debug mode
- `SECRET_KEY`: Flask secret key for sessions

### Database Configuration
- Database file: `src/database/app.db`
- Automatic table creation on first run
- SQLAlchemy ORM for database operations

## 📱 Browser Compatibility

- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge
- Mobile browsers (iOS Safari, Chrome Mobile)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues or questions:
1. Check the browser console for error messages
2. Verify the Flask server is running
3. Ensure all dependencies are installed
4. Check network connectivity for the deployed version

## 🎯 Future Enhancements

Potential improvements for future versions:
- User authentication and multi-user support
- Note categories and tags
- Rich text formatting (bold, italic, lists)
- File attachments
- Export functionality (PDF, Markdown)
- Dark/light theme toggle
- Offline support with service workers
- Note sharing capabilities

---

**Built with ❤️ using Flask, SQLite, and modern web technologies**
