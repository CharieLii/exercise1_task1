# NoteTaker - Personal Note Management Application

A modern, responsive web application for managing personal notes with a beautiful user interface and full CRUD functionality.

## 🌟 Features

- **Create Notes**: Add new notes with titles and rich content
- **Edit Notes**: Update existing notes with real-time editing
- **Delete Notes**: Remove notes you no longer need
- **Search Notes**: Find notes quickly by searching titles and content
- **Auto-save**: Notes are automatically saved as you type
- **Responsive Design**: Works perfectly on desktop and mobile devices
- **Modern UI**: Blue and white design with responsive layouts
- **Real-time Updates**: Instant feedback and updates
- **Image Attachments**: Upload, preview, open, and remove images stored in Neon

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
- **Neon PostgreSQL**: Cloud database for notes and image bytes (`BYTEA`)

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
│   ├── app.py               # Application factory and database CLI
│   ├── database.py          # Neon configuration and SQLite import
│   └── main.py              # Flask application entry point
├── database/app.db          # Legacy SQLite data retained for migration
├── .env.example             # Configuration template (no credentials)
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

4. **Configure and initialize Neon**
   Create a project in the [Neon Console](https://console.neon.tech). Open
   **Connect**, select the branch/database/role, and copy the PostgreSQL
   connection string (the pooled connection is suitable for the app).
   Add it to your local `.env`, keeping the existing `open_router_key`:
   ```dotenv
   DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
   ```
   Preserve any additional parameters such as `channel_binding=require` from
   the Neon connection string. `.env` is ignored by Git; `.env.example` has
   placeholders only. The application requires PostgreSQL and does not
   silently fall back to SQLite when configuration is absent.

   ```bash
   python -m flask --app src.app:create_app db-check
   python -m flask --app src.app:create_app init-db
   ```

5. **Migrate existing SQLite notes (optional, before creating new notes)**
   Stop the old app first so no more notes are written to SQLite. Import into
   an empty initialized Neon database:
   ```bash
   python -m flask --app src.app:create_app migrate-sqlite --source database/app.db
   ```
   This copies note/user IDs, text, and timestamps, then adjusts PostgreSQL ID
   sequences. It preserves the source file and refuses to import into a
   database that already has notes, users, or images. A failed import rolls
   back inserted records. Existing SQLite images are not imported by this
   command; the original app did not have an image table.

6. **Run the application**
   ```bash
   python src/main.py
   ```

7. **Access the application**
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

### Image Attachments

Save a note, then choose a file in **Images → Attach image**. Images are uploaded
immediately; no additional Save click is needed. Click a thumbnail to open the
original, or **Remove image** to delete it. Deleting a note also deletes its
images. Text editing and translation continue to work as before.

- `POST /api/notes/<id>/images`: multipart upload with a field named `image`
- `GET /api/notes/<id>/images/<image_id>`: original image bytes with the verified MIME type
- `DELETE /api/notes/<id>/images/<image_id>`: delete the image (HTTP 204)
- Note JSON includes `images` metadata (ID, filename, MIME type, size, URL),
  without image bytes or base64 in note lists.

Supported formats: PNG, JPEG, GIF, WebP, HEIC/HEIF. HEIC/HEIF files (including
files incorrectly named `.jpg`) are detected by their contents and converted
to JPEG for browser previews. Only the primary image is retained; animation or
additional HEIF images are not preserved. The converted file must also fit
within 5 MB. Maximum 5 MB and 40 megapixels per image.
The server validates actual file contents rather than trusting the filename or
browser MIME type. Files are stored in PostgreSQL `BYTEA` via a separate
`note_image` table; no persistent upload directory or object-storage account is
required. This is intended for small image attachments; larger media can later
move to a dedicated object store.

Run offline database/image/translation checks with:

```bash
python -m unittest discover -s tests -v
```

Tests use disposable in-memory SQLite databases, not your legacy database or
Neon. A real cloud smoke test is still needed after configuring `DATABASE_URL`:
create a note, attach an image, restart the app, reopen the note and verify that
the image remains available.

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🚀 Deployment to Vercel

The root `app.py` exports the Flask application, `.python-version` selects
Python 3.12, and `vercel.json` configures the Flask preset and a 180-second
function limit. The build command copies the canonical `src/static` frontend
to `public/` for Vercel's CDN. Keep editing `src/static/index.html` locally.

Import `CharieLii/exercise1_task1` into the `charielii` Vercel account. Use
`main` as the Production Branch, root directory `.`, and the Flask framework
preset. Configure `DATABASE_URL` and `open_router_key` as server environment
variables; optionally set a stable `SECRET_KEY`. Do not upload `.env` or the
legacy database. The Neon tables have already been initialized and migrated;
no migration runs during builds or function startup.

Vercel deployment uses a 4 MB image limit so multipart requests stay within
its 4.5 MB function payload limit. The UI fetches the active limit from
`/api/config`; local development keeps the 5 MB limit. HEIC conversion is
subject to the same stored-file limit. Larger uploads would require a direct
object-storage upload flow.

After deployment, check the home page, `/api/notes`, a small image upload,
and translation. The existing app has no user login or per-user ownership;
its note and image APIs are shared by visitors to the deployment.

## 🔧 Configuration

### Environment Variables
- `DATABASE_URL`: Required Neon PostgreSQL connection string
- `open_router_key`: OpenRouter API credential for translation
- `SECRET_KEY`: Flask secret key for sessions

### Database Configuration
- Neon PostgreSQL via SQLAlchemy and Psycopg 3, with SSL enabled
- Explicit table initialization via `init-db`; application startup does not create tables
- Small connection pool with stale-connection checks
- SQLite is only used by offline tests and the read-only legacy import

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
- Document attachments (image attachments are already supported)
- Export functionality (PDF, Markdown)
- Dark/light theme toggle
- Offline support with service workers
- Note sharing capabilities

---

**Built with Flask, Neon PostgreSQL, and modern web technologies**
