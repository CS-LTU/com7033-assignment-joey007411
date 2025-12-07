# Medical Dashboard

A web-based medical dashboard for managing patient data, built with Flask and MongoDB. The application includes features for user authentication, patient management, and data visualization.

## Features

- **User Authentication**: Secure login and registration system.
- **Patient Management**: Add, update, and delete patient records.
- **Data Visualization**: Dashboard with statistics such as average BMI, glucose levels, and stroke distribution.
- **Pagination**: View patient lists with pagination for better usability.
- **Encryption**: Optional encryption for sensitive patient data.

## Prerequisites

- Python 3.8 or higher
- MongoDB
- SQLite (for user authentication)
- Node.js (optional, for managing frontend dependencies)

## Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd ltuassignment
   ```

2. **Set Up a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**:
   Create a `.env` file in the root directory and add the following:
   ```
   FLASK_SECRET_KEY=your_secret_key
   MONGO_URI=mongodb://localhost:27017
   MONGO_DB=healthcare
   MONGO_COLLECTION=patients
   ```

5. **Initialize the Database**:
   - MongoDB: Ensure the `healthcare` database and `patients` collection exist.
   - SQLite: The `users.db` file will be created automatically.

6. **Run the Application**:
   ```bash
   flask run
   ```

7. **Access the Application**:
   Open your browser and navigate to `http://127.0.0.1:5000`.

## Usage

- **Login**: Use the demo credentials (`doctor@example.com` / `password`) or create a new account.
- **Dashboard**: View statistics and recent patient data.
- **Patient List**: Browse all patients with pagination.
- **Add/Update Patient**: Add new patients or update existing records.

## File Structure

```
ltuassignment/
├── app/
│   ├── templates/          # HTML templates
│   ├── static/             # Static files (CSS, JS)
│   ├── helpers/            # Helper modules
│   ├── route.py            # Flask routes
│   ├── __init__.py         # Flask app factory
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── README.md               # Project documentation
```

## Troubleshooting

- **MongoDB Connection Issues**:
  Ensure MongoDB is running and the `MONGO_URI` in `.env` is correct.

- **Invalid ObjectId Errors**:
  If patient IDs are not valid MongoDB ObjectIds, ensure the `id` field is used for querying.

- **CSS Issues**:
  Ensure Tailwind CSS is loaded correctly via the CDN.

## License

This project is licensed under the MIT License.


